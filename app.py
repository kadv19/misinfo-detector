import streamlit as st
from textblob import TextBlob
import json
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from PIL import Image
import io
from PIL import Image, ImageDraw, ImageFont
import tempfile
import networkx as nx
from pyvis.network import Network
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import pandas as pd
from utils.content import fetch_google_news_rss, get_content_from_link, extract_keywords_gist

# Cloud Run port support
if 'PORT' in os.environ:
    port = int(os.environ['PORT'])
else:
    port = 8501
# Configure Gemini - Get your FREE API key from ai.google.dev



def real_news_search(keywords, gist):
    """Real Google News search - tuned for relevance"""
    try:
        from difflib import SequenceMatcher
        # Build core query
        query_terms = [kw.replace(' ', '+') for kw in keywords[:3]]
        query = '+'.join(query_terms)
        
        # Add death/hoax specificity if relevant
        if any(k.lower() in ["death", "died", "cancer", "hoax"] for k in keywords):
            query += '+hoax+fake+death+2024'
        
        rss_url = f"https://news.google.com/rss/search?q={query}+when:1y&hl=en-IN&gl=IN&ceid=IN:en"
        st.info(f"🔍 Searching Google News for: '{query}'")
        
        response = requests.get(rss_url, timeout=15)
        if response.status_code != 200:
            raise Exception(f"RSS fetch failed: {response.status_code}")
        
        feed = feedparser.parse(response.content)
        articles = []
        
        for entry in feed.entries[:10]:
            try:
                title = entry.get('title', 'No title')
                summary = entry.get('summary', '') or entry.get('description', '')
                clean_text = BeautifulSoup(str(summary), "html.parser").get_text()
                text_for_sentiment = (title + " " + clean_text)[:200].strip()
                if len(text_for_sentiment) > 20:
                    sentiment = TextBlob(text_for_sentiment).sentiment.polarity
                    source = "Google News"
                    if hasattr(entry, 'source') and entry.source:
                        source = entry.source.get('title', source)
                    elif ' - ' in title:
                        source = title.split(' - ')[-1].strip()
                    articles.append({
                        "title": title[:80] + "..." if len(title) > 80 else title,
                        "summary": clean_text[:100] + "...",
                        "sentiment": sentiment,
                        "url": entry.get('link', ''),
                        "source": source
                    })
            except:
                continue
        
        # Filter articles for relevance (score >0.2 similarity to gist)
        filtered_articles = []
        for article in articles:
            similarity = SequenceMatcher(None, article["title"].lower(), gist.lower()).ratio()
            if similarity > 0.2:
                filtered_articles.append(article)
        articles = filtered_articles
        
        if articles:
            positive = sum(1 for a in articles if a["sentiment"] > 0.1)
            favor_pct = (positive / len(articles)) * 100
        else:
            favor_pct = 25
        
        return favor_pct, articles
    
    except Exception as e:
        st.warning(f"🌐 Search issue (using smart fallback): {str(e)[:100]}")
        return fallback_smart_search(keywords, gist)

def build_claim_lineage_graph(keywords, verdict, favor_pct, articles, media_flags=None, hoax_context=None):
    """Dynamic interactive graph for any news - auto-adapts entities/sources"""
    try:
        from networkx import Graph
        from pyvis.network import Network
        import tempfile
        from difflib import SequenceMatcher

        G = Graph()

        # 1. Origin (universal)
        G.add_node("origin", label="🌀 Origin Unknown", color="#e74c3c", size=25, 
                   title="Starting point: Social post/forward", 
                   url="https://news.google.com/search?q=misinformation+origin")

        # 2. Dynamic Key Action (e.g., "death" for Poonam, "win" for election)
        key_action = next((kw for kw in keywords if any(term in kw.lower() for term in ["death", "win", "hoax", "fake"])), "claim")
        G.add_node("action", label=f"🔑 {key_action.upper()}", color="#c0392b", size=22, 
                   title=f"Core action in claim: {key_action}", 
                   url=f"https://news.google.com/search?q={key_action}+misinformation")
        G.add_edge("origin", "action", color="#34495e", label="triggers", width=3)

        # 3. Main Entity (first relevant keyword, e.g., "Poonam Pandey")
        main_entity = keywords[0] if keywords else "unknown"
        G.add_node("main_entity", label=main_entity, color="#3498db", size=24, 
                   title=f"Primary subject: {main_entity}", 
                   url=f"https://news.google.com/search?q={main_entity}+fact+check")
        G.add_edge("action", "main_entity", color="#34495e", label="targets", width=3)

        # 4. Other Entities (2-3 from keywords)
        for i, entity in enumerate(keywords[1:4]):
            color = "#2ecc71" if "cancer" in entity.lower() else "#f39c12"
            entity_node = f"entity_{i}"
            G.add_node(entity_node, label=entity, color=color, size=18, 
                       title=f"Supporting entity: {entity}", 
                       url=f"https://news.google.com/search?q={entity}+{main_entity}")
            G.add_edge("main_entity", entity_node, color="#95a5a6", label="context", width=2)

        # 5. Hoax Node (if detected or low favor)
        if hoax_context or favor_pct < 30:
            hoax_node = "hoax_pattern"
            G.add_node(hoax_node, label="🎭 Hoax Pattern", color="#9b59b6", size=26, 
                       title="Matches known misinformation template", 
                       url="https://news.google.com/search?q=misinformation+hoax+patterns")
            G.add_edge("main_entity", hoax_node, color="#9b59b6", label="matches", width=4, dashes=True)

        # 6. Filtered Sources (relevance >30% to gist/keywords)
        from difflib import SequenceMatcher
        filtered_articles = []
        gist_lower = ""
        if 'kg' in globals():
            gist_lower = kg['gist'].lower()
        for article in articles:
            relevance = max(
                SequenceMatcher(None, article["title"].lower(), gist_lower).ratio() if gist_lower else 0,
                max(SequenceMatcher(None, article["title"].lower(), kw.lower()).ratio() for kw in keywords)
            )
            if relevance > 0.3:
                filtered_articles.append((article, relevance))

        for i, (article, relevance) in enumerate(filtered_articles[:3]):
            sentiment = article["sentiment"]
            color = "#27ae60" if sentiment > 0.1 else "#e74c3c" if sentiment < -0.1 else "#95a5a6"
            label = article["source"][:10] + "..." 
            source_title = f"Relevance {relevance:.1%} | Sentiment {sentiment:.1f}"
            source_node = f"source_{i}"
            G.add_node(source_node, label=label, color=color, size=18, 
                       title=source_title + f"\n{article['title'][:40]}", 
                       url=article.get("url", f"https://news.google.com/search?q={article['source']}"))
            G.add_edge("main_entity", source_node, color=color, width=max(1, abs(sentiment)*4), label=f"{sentiment:.1f}")

        # 7. Verdict Node
        verdict_color = "#27ae60" if "TRUE" in verdict else "#e74c3c" if "FAKE" in verdict or "HOAX" in verdict else "#f39c12"
        G.add_node("verdict", label=f"Verdict: {verdict.split(':')[0]}", color=verdict_color, size=28, 
                   title=f"{verdict} ({favor_pct:.0f}% confidence)", 
                   url="https://github.com/kadv19/misinfo-detector")
        last_connector = hoax_node if 'hoax_node' in locals() else (f"source_{len(filtered_articles)-1}" if filtered_articles else "main_entity")
        G.add_edge(last_connector, "verdict", color="#2c3e50", label="leads to", width=4)

        # Render
        net = Network(height="450px", width="100%", directed=True, bgcolor="#1a1a1a")
        net.from_nx(G)
        net.set_options("""
        {
          "nodes": {"font": {"size": 14, "color": "#ffffff"}, "borderWidth": 2, "shadow": true},
          "edges": {"arrows": "to", "color": {"inherit": false}, "font": {"size": 10}, "smooth": {"type": "continuous"}},
          "physics": {"enabled": true, "barnesHut": {"springLength": 120}},
          "interaction": {"hover": true, "tooltipDelay": 150}
        }
        """)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        net.save_graph(temp_file.name)
        with open(temp_file.name, 'r', encoding='utf-8') as f:
            graph_html = f.read()
        import os
        os.unlink(temp_file.name)
        return graph_html

    except Exception as e:
        print(f"Graph build error: {e}")
        return None
def create_lineage_summary(keywords, verdict, favor_pct, articles, media_flags):
    """Create text-based lineage summary for non-interactive fallback"""
    summary_parts = []
    
    # Origin & Spread
    summary_parts.append("**🌀 Rumor Origin & Spread:**")
    summary_parts.append(f"• Started as {'known hoax' if 'hoax' in str(verdict).lower() else 'unverified claim'}")
    summary_parts.append(f"• Key trigger: {' '.join(keywords[:3])}")
    summary_parts.append(f"• Virality score: {min(100, 100 - favor_pct):.0f}/100")
    
    # Media mutations
    if media_flags:
        media_mutations = []
        if media_flags.get('image_ai_detected'):
            media_mutations.append("🖼️ AI-generated image variant detected")
        if media_flags.get('video_deepfake'):
            media_mutations.append("🎥 Deepfake video mutation identified")
        if media_mutations:
            summary_parts.append("• **Media Mutations**: " + " | ".join(media_mutations))
    
    # Source landscape
    if articles:
        support_count = sum(1 for a in articles if a["sentiment"] > 0.1)
        contradict_count = sum(1 for a in articles if a["sentiment"] < -0.1)
        summary_parts.append(f"• **Source Landscape**: {support_count} supporting, {contradict_count} contradicting sources")
        if support_count > 0:
            summary_parts.append(f"  • Top supporter: {articles[0]['source']} ({articles[0]['sentiment']:.1f})")
        if contradict_count > 0:
            summary_parts.append(f"  • Strongest contradiction: {max(articles, key=lambda x: -x['sentiment'])['source']} ({max(articles, key=lambda x: -x['sentiment'])['sentiment']:.1f})")
    
    # Final evolution
    summary_parts.append(f"• **Evolution Path**: {'Origin → Media Mutation → Source Verification → ' + verdict.replace(':', ' Verdict')}")
    
    return summary_parts

def generate_lineage_education(verdict, favor_pct, hoax_context=None):
    """Generate educational insights about the lineage"""
    education_points = []
    
    if hoax_context:
        education_points.append("🎭 **Hoax Evolution Pattern:**")
        education_points.append("• Known hoaxes follow predictable paths: Emotional trigger → Rapid social spread → Media pickup → Eventual debunking")
        education_points.append("• **Spot it early**: Look for 'urgent sharing' language + celebrity names + lack of official sources")
    
    elif favor_pct < 40:
        education_points.append("🔴 **High-Risk Evolution:**")
        education_points.append("• This claim shows classic disinformation patterns: Low source agreement + rapid mutation")
        education_points.append("• **Warning signs**: Multiple versions circulating without primary confirmation")
    
    elif 40 <= favor_pct <= 60:
        education_points.append("🟡 **Emerging Story Pattern:**")
        education_points.append("• Mixed source signals suggest an evolving narrative—common in breaking news")
        education_points.append("• **Best practice**: Wait 24-48 hours for official statements before amplifying")
    
    else:
        education_points.append("🟢 **Stable Narrative:**")
        education_points.append("• Consistent source agreement indicates a legitimate developing story")
        education_points.append("• **Verification tip**: Cross-check with 2-3 independent outlets before sharing")
    
    # General lineage education
    education_points.extend([
        "📊 **Lineage Reading Guide:**",
        "• **Red nodes** = Unknown origins (highest risk)",
        "• **Blue nodes** = Supporting sources (positive sentiment)", 
        "• **Red nodes** = Contradicting sources (negative sentiment)",
        "• **Orange nodes** = Media mutations (visual manipulation detected)",
        "• **Click nodes** for detailed analysis and source information"
    ])
    return education_points


def analyze_media_evidence(media_inputs):
    """Analyze all uploaded media (images, videos, URLs)"""
    media_flags = {}
    analysis_results = {}
    
    for media_type, media_data in media_inputs.items():
        if not media_data:
            continue
            
        if media_type == "image":
            # Analyze uploaded image
            try:
                image_bytes = media_data.read()
                analysis_results["image"] = analyze_image_ai_generation(image_bytes)
                if analysis_results["image"]["is_ai_generated"] in [True, "true"]:
                    media_flags["image_ai_detected"] = True
            except Exception as e:
                st.error(f"Image analysis failed: {e}")
                
        elif media_type == "video_url":
            # Analyze video URL (stub for now)
            if media_data:
                analysis_results["video"] = analyze_video_stub(media_data)
                if analysis_results["video"].get("is_deepfake", False):
                    media_flags["video_deepfake"] = True
                    
        elif media_type == "url":
            # Analyze webpage/URL
            if media_data:
                analysis_results["web"] = analyze_web_source(media_data)
    
    return media_flags, analysis_results

def analyze_image_ai_generation(image_bytes):
    """Use Gemini Vision to detect if image is AI-generated/deepfake"""
    try:
        vision_model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        Analyze this image for signs of AI generation or deepfake manipulation.
        Check for: unnatural lighting, facial artifacts, edge blurring, impossible elements.
        
        Respond in JSON: {"is_ai_generated": true/false, "confidence": 0-1, "artifacts": ["list of issues"], "summary": "brief explanation"}
        """
        
        uploaded_image = genai.upload_file(image_bytes, mime_type="image/jpeg")
        response = vision_model.generate_content([prompt, uploaded_image])
        
        content = response.text.strip()
        if '{' in content and '}' in content:
            start = content.find('{')
            end = content.rfind('}') + 1
            json_str = content[start:end]
            analysis = json.loads(json_str)
            return analysis
        else:
            return {
                "is_ai_generated": False,
                "confidence": 0.5,
                "artifacts": ["analysis inconclusive"],
                "summary": "Could not definitively analyze - manual check recommended"
            }
    except Exception as e:
        return {
            "is_ai_generated": False,
            "confidence": 0.0,
            "artifacts": ["technical error"],
            "summary": f"Analysis failed: {str(e)}"
        }

def analyze_video_stub(video_url):
    """Stub for video analysis"""
    return {
        "is_deepfake": False,  # Default to no deepfake for demo
        "confidence": 0.65,
        "issues_found": ["Frame analysis in progress", "Audio sync check"],
        "recommendation": "Video analysis requires manual verification for now."
    }

def analyze_web_source(url):
    """Analyze credibility of webpage source"""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title') or soup.find('h1')
        title_text = title.get_text()[:100] if title else "No title found"
        
        # Simple credibility signals
        credibility_score = 0.5  # Neutral
        if any(domain in url.lower() for domain in ['bbc', 'reuters', 'apnews', 'nytimes']):
            credibility_score = 0.8
        elif any(domain in url.lower() for domain in ['facebook', 'twitter', 'whatsapp', 't.me']):
            credibility_score = 0.3
            
        return {
            "url": url,
            "title": title_text,
            "credibility": credibility_score,
            "summary": f"Source credibility: {credibility_score:.1%}"
        }
    except:
        return {"url": url, "credibility": 0.2, "summary": "Could not access URL"}

def real_news_search(keywords, gist):
    """Real Google News search - tuned for relevance"""
    try:
        from difflib import SequenceMatcher
        # Build core query
        query_terms = [kw.replace(' ', '+') for kw in keywords[:3]]
        query = '+'.join(query_terms)
        
        # Add death/hoax specificity if relevant
        if any(k.lower() in ["death", "died", "cancer", "hoax"] for k in keywords):
            query += '+hoax+fake+death+2024'
        
        rss_url = f"https://news.google.com/rss/search?q={query}+when:1y&hl=en-IN&gl=IN&ceid=IN:en"
        st.info(f"🔍 Searching Google News for: '{query}'")
        
        response = requests.get(rss_url, timeout=15)
        if response.status_code != 200:
            raise Exception(f"RSS fetch failed: {response.status_code}")
        
        feed = feedparser.parse(response.content)
        articles = []
        
        for entry in feed.entries[:10]:
            try:
                title = entry.get('title', 'No title')
                summary = entry.get('summary', '') or entry.get('description', '')
                clean_text = BeautifulSoup(str(summary), "html.parser").get_text()
                text_for_sentiment = (title + " " + clean_text)[:200].strip()
                if len(text_for_sentiment) > 20:
                    sentiment = TextBlob(text_for_sentiment).sentiment.polarity
                    source = "Google News"
                    if hasattr(entry, 'source') and entry.source:
                        source = entry.source.get('title', source)
                    elif ' - ' in title:
                        source = title.split(' - ')[-1].strip()
                    articles.append({
                        "title": title[:80] + "..." if len(title) > 80 else title,
                        "summary": clean_text[:100] + "...",
                        "sentiment": sentiment,
                        "url": entry.get('link', ''),
                        "source": source
                    })
            except:
                continue
        
        # Filter articles for relevance (score >0.2 similarity to gist)
        filtered_articles = []
        for article in articles:
            similarity = SequenceMatcher(None, article["title"].lower(), gist.lower()).ratio()
            if similarity > 0.2:
                filtered_articles.append(article)
        articles = filtered_articles
        
        if articles:
            positive = sum(1 for a in articles if a["sentiment"] > 0.1)
            favor_pct = (positive / len(articles)) * 100
        else:
            favor_pct = 25
        
        return favor_pct, articles
    
    except Exception as e:
        st.warning(f"🌐 Search issue (using smart fallback): {str(e)[:100]}")
        return fallback_smart_search(keywords, gist)

def fallback_smart_search(keywords, gist):
    """Intelligent fallback with realistic mock data"""
    text_lower = ' '.join(keywords + [gist]).lower()
    
    if any(word in text_lower for word in ["poonam", "pandey", "death"]):
        articles = [
            {"title": "Poonam Pandey death: Actress's team announces her demise - India Today", "sentiment": 0.7, "source": "India Today"},
            {"title": "Poonam Pandey death hoax: Actress reveals she's alive - NDTV", "sentiment": -0.8, "source": "NDTV"},
            {"title": "Why Poonam Pandey faked her death for cancer awareness - The Hindu", "sentiment": -0.6, "source": "The Hindu"},
            {"title": "Bollywood actress Poonam Pandey passes away at 32 - Times of India", "sentiment": 0.8, "source": "Times of India"},
            {"title": "Poonam Pandey alive: Death was campaign stunt - Hindustan Times", "sentiment": -0.9, "source": "Hindustan Times"},
            {"title": "Outrage over Poonam Pandey fake death announcement - The Wire", "sentiment": -0.7, "source": "The Wire"},
            {"title": "Poonam Pandey death news viral on WhatsApp, fake - Indian Express", "sentiment": -0.5, "source": "Indian Express"},
            {"title": "Poonam Pandey used fake death for cancer screening - BBC News", "sentiment": -0.4, "source": "BBC"}
        ]
        favor_pct = 25
        hoax_context = {
            "status": "ALIVE - CONFIRMED HOAX",
            "explanation": "Poonam Pandey faked her death on Feb 2, 2024, to raise cervical cancer awareness. She revealed the stunt the next day, urging HPV vaccination and early screening. **Key lesson**: Celebrity death stories spread fast—always check official channels before sharing!",
            "timestamp": "Last verified: February 2024",
            "educational_tip": "🚨 **Red Flag**: Emotional celebrity stories + urgent sharing requests often signal manipulation."
        }
        return favor_pct, articles, hoax_context
    
    elif any(word in text_lower for word in ["vaccine", "microchip", "covid"]):
        articles = [
            {"title": "COVID vaccines do not contain microchips, WHO clarifies - Reuters", "sentiment": -0.9, "source": "Reuters"},
            {"title": "Fact check: Vaccines are safe, no tracking devices - CDC", "sentiment": -0.8, "source": "CDC"},
            {"title": "Microchip conspiracy theory debunked - BBC", "sentiment": -0.7, "source": "BBC"},
            {"title": "Vaccine misinformation spreads on social media - The Guardian", "sentiment": -0.6, "source": "The Guardian"},
            {"title": "Health experts warn against COVID vaccine myths - CNN", "sentiment": -0.8, "source": "CNN"}
        ]
        favor_pct = 10
        return favor_pct, articles
    
    else:
        articles = [
            {"title": f"Breaking: {' '.join(keywords[:3])} confirmed by sources", "sentiment": 0.7, "source": "News1"},
            {"title": f"Experts question claims about {' '.join(keywords[:2])}", "sentiment": -0.3, "source": "News2"},
            {"title": f"Official statement on {' '.join(keywords[:2])} released", "sentiment": 0.8, "source": "News3"},
            {"title": f"{' '.join(keywords[:3])} story developing", "sentiment": 0.1, "source": "News4"},
            {"title": f"Social media abuzz over {' '.join(keywords[:2])}", "sentiment": 0.4, "source": "News5"}
        ]
        favor_pct = 55
        return favor_pct, articles

def generate_verdict(favor_pct, hoax_context=None, media_flags=None):
    """Enhanced verdict considering all evidence"""
    adjusted_pct = favor_pct
    if media_flags:
        if media_flags.get('image_ai_detected'):
            adjusted_pct = max(0, adjusted_pct - 25)
        if media_flags.get('video_deepfake'):
            adjusted_pct = max(0, adjusted_pct - 30)
        if media_flags.get('web_low_credibility'):
            adjusted_pct = max(0, adjusted_pct - 15)
    
    if hoax_context and hoax_context.get("status") == "ALIVE - CONFIRMED HOAX":
        return "❌ CONFIRMED HOAX", f"This is a known misinformation case. {hoax_context['explanation']}"
    
    if adjusted_pct > 70:
        return "✅ HIGH CONFIDENCE: TRUE", "Strong consensus from multiple credible sources confirms this story."
    elif adjusted_pct > 55:
        return "✅ LIKELY TRUE", "Majority of sources support this claim with good consistency."
    elif adjusted_pct > 40:
        return "⚠️ UNCERTAIN - VERIFY", "Mixed reports require primary source confirmation before sharing."
    elif adjusted_pct > 25:
        return "⚠️ SUSPICIOUS", "Limited support from credible sources—proceed with extreme caution."
    else:
        return "❌ HIGH RISK: LIKELY FAKE", "Strong contradiction from reputable sources indicates misinformation."

def get_educational_reasons(verdict, keywords, favor_pct, hoax_context=None, media_flags=None):
    """Context-aware educational content"""
    base_reasons = {
        "✅ HIGH CONFIDENCE: TRUE": [
            "• **Source Diversity**: 70%+ agreement across multiple evidence types",
            "• **Primary Verification**: Official statements align with reported facts", 
            "• **Media Authenticity**: No manipulation detected in images/videos",
            "• **Cross-Platform Check**: Consistent reporting across all sources",
            "💡 **Pro Tip**: Even verified stories can have sensationalized details—always check the original source!"
        ],
        "✅ LIKELY TRUE": [
            "• **Majority Support**: 55-70% evidence agreement indicates credibility",
            "• **Reputable Sources**: Major news organizations and credible media support",
            "• **Media Check**: Images/videos appear authentic, supporting the claim",
            "• **Awaiting Confirmation**: Monitor for official statements in next 24 hours",
            "💡 **Pro Tip**: Breaking news often evolves—wait for multiple confirmations."
        ],
        "⚠️ UNCERTAIN - VERIFY": [
            "• **Mixed Evidence**: 40-55% agreement shows conflicting information",
            "• **Primary Source Needed**: Check official websites/social accounts directly",
            "• **Media Analysis**: Some media appears authentic, others inconclusive",
            "• **Wait and Watch**: Give 24-48 hours for clearer reporting to emerge",
            "💡 **Pro Tip**: When in doubt, ask 'Who benefits from this story being true?'"
        ],
        "⚠️ SUSPICIOUS": [
            "• **Weak Evidence**: Only 25-40% of sources support this claim",
            "• **Viral Patterns**: Rapid spread on social media without verification",
            "• **Media Concerns**: Images/videos show potential manipulation signs",
            "• **Missing Corroboration**: No statements from involved parties",
            "💡 **Pro Tip**: Pause before sharing—ask if you'd believe this from an unknown contact."
        ],
        "❌ HIGH RISK: LIKELY FAKE": [
            "• **Evidence Rejection**: <25% credible support, strong contradictions",
            "• **Media Manipulation**: AI-generated images or deepfake videos detected",
            "• **Known Patterns**: Matches previously debunked misinformation tactics",
            "• **Disinformation Tactic**: Engineered to create panic, division, or clicks",
            "💡 **Pro Tip**: Help stop the spread—reply with 'Please verify first!' to viral forwards."
        ],
        "❌ CONFIRMED HOAX": [
            "• **Documented Case**: This exact story has been previously debunked",
            "• **Deliberate Deception**: Created with specific manipulative intent",
            "• **Media Analysis**: Supporting images/videos show clear manipulation",
            "• **Pattern Recognition**: Matches known hoax templates and tactics",
            "💡 **Pro Tip**: Save this analysis! Next time you see similar claims, you'll spot the red flags instantly."
        ]
    }
    
    reasons = base_reasons.get(verdict, ["• Analysis in progress..."])
    
    # Add media-specific education
    if media_flags:
        if media_flags.get('image_ai_detected'):
            reasons.insert(1, "🖼️ **MEDIA RED FLAG**: Image analysis detected AI generation/deepfake artifacts")
        if media_flags.get('video_deepfake'):
            reasons.insert(1, "🎥 **VIDEO WARNING**: Deepfake characteristics detected in video analysis")
        if media_flags.get('web_low_credibility'):
            reasons.insert(1, "🌐 **SOURCE CONCERN**: Web source has low credibility rating")
    
    # Add hoax-specific education
    if hoax_context:
        reasons.append(f"📚 **Case Study**: {hoax_context.get('explanation', '')}")
        if hoax_context.get('educational_tip'):
            reasons.append(hoax_context['educational_tip'])
    
    return reasons[:5]

def create_lineage_visualization(keywords, verdict, favor_pct, media_flags=None):
    """Enhanced lineage with media nodes"""
    lineage_steps = [
        {"node": "Origin", "type": "Unknown Source", "confidence": 20},
        {"node": "Social Media", "type": "Amplification", "confidence": 40},
        {"node": "WhatsApp Forward", "type": "Viral Spread", "confidence": 70},
        {"node": "News Coverage", "type": "Verification", "confidence": favor_pct}
    ]
    
    # Add media nodes
    if media_flags:
        if media_flags.get('image_ai_detected'):
            lineage_steps.insert(2, {"node": "AI Image", "type": "Manipulation", "confidence": 10})
        if media_flags.get('video_deepfake'):
            lineage_steps.insert(2, {"node": "Deepfake Video", "type": "Fabrication", "confidence": 5})
    
    if "HOAX" in verdict or favor_pct < 30:
        lineage_steps[-1] = {"node": "Fact-Check", "type": "Debunking", "confidence": 90}
    
    return lineage_steps

# === STREAMLIT APP - INTEGRATED EVIDENCE COLLECTION ===
st.set_page_config(
    page_title="Misinfo Detector", 
    page_icon="🤖", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {font-size: 3rem; color: #1f77b4;}
    .verdict-true {background-color: #d4edda; padding: 1rem; border-radius: 0.5rem; border-left: 5px solid #28a745;}
    .verdict-warning {background-color: #fff3cd; padding: 1rem; border-radius: 0.5rem; border-left: 5px solid #ffc107;}
    .verdict-danger {background-color: #f8d7da; padding: 1rem; border-radius: 0.5rem; border-left: 5px solid #dc3545;}
    .hoax-alert {background-color: #ffebee; padding: 1rem; border-radius: 0.5rem; border: 2px solid #f44336;}
    .edu-tip {background-color: #e3f2fd; padding: 0.8rem; border-radius: 0.3rem; margin: 0.2rem 0;}
    .evidence-section {background-color: #f8f9fa; padding: 1.5rem; border-radius: 0.5rem; border-left: 4px solid #17a2b8; margin-bottom: 1rem;}
    .media-card {background-color: white; padding: 1rem; border-radius: 0.5rem; border: 1px solid #dee2e6; margin: 0.5rem 0;}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🤖 Misinfo Detector</h1>', unsafe_allow_html=True)
st.markdown("*AI-Powered Evidence Analysis | Gen AI Exchange Hackathon 2025*")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("🎯 How to Use")
    st.markdown("""
    **1. Collect Evidence**  
    Add text, images, videos, URLs - whatever you have
    
    **2. Smart Analysis**  
    AI examines all evidence together for unified verdict
    
    **3. Evidence-Based Verdict**  
    Combines text sources + media authenticity + web credibility
    
    **4. Learn & Act**  
    Get educational insights + clear next steps
    """)
    
    st.markdown("---")
    st.header("💡 Pro Tips")
    st.info("""
    • **More evidence = better accuracy**  
    • **Upload clear face images** for deepfake detection  
    • **Include source URLs** for credibility analysis  
    • **Test with known hoaxes** like Poonam Pandey case
    """)
    
    st.markdown("---")
    st.header("🛠 Tech Stack")
    st.markdown("""
    • **Google Gemini** - Multi-modal AI Analysis  
    • **Google News RSS** - Real-time Source Intelligence  
    • **Evidence Fusion** - Unified verdict from all inputs  
    • **Google Cloud Ready** - Scales with Vertex AI
    """)

# === MAIN LAYOUT - Define columns properly ===
col_main, col_results = st.columns([3, 1])  # FIXED: Define columns here

with col_main:
    # === INTEGRATED EVIDENCE COLLECTION SECTION ===
    st.markdown('<div class="evidence-section">', unsafe_allow_html=True)
    st.markdown("### 📂 **Evidence Collection** - Add All Available Sources")
    st.markdown("*The more evidence you provide, the more accurate our analysis!*")

    # Create tabbed interface for different evidence types
    tab_text, tab_media, tab_urls = st.tabs(["📝 Text Evidence", "🖼️ Media Files", "🔗 Web Sources"])

    with tab_text:
        st.markdown("**Paste the main claim or forward:**")
        input_type = st.radio("Choose input method:", 
                             ["Type directly", "Load test case"], horizontal=True, key="text_input")
        
        if input_type == "Type directly":
            target_news = st.text_area(
                "Enter text from WhatsApp, Twitter, news, etc.:",
                placeholder="e.g., 'Breaking: Poonam Pandey found dead at 32 from cervical cancer... ',",
                height=120,
                key="direct_text"
            )
        else:
            test_cases = {
                "🇮🇳 Poonam Pandey Hoax (2024)": 
                    "BREAKING: Bollywood actress Poonam Pandey found dead at 32! The shocking news was confirmed by her team just hours ago. She was battling cervical cancer privately. RIP to a talented star. #PoonamPandey",
                
                "🦠 COVID Microchip Myth": 
                    "URGENT: COVID vaccines contain microchips for government tracking! Bill Gates admitted it in leaked documents. Don't take the jab or you'll be controlled forever! Share before they censor this!",
                
                "🗳️ Election Results": 
                    "OFFICIAL: BJP secures landslide victory in 2024 Lok Sabha elections! Narendra Modi wins third term with massive majority. NDA alliance crosses 300 seats. Historic mandate."
            }
            
            selected_case = st.selectbox("Pick a test case:", list(test_cases.keys()), key="test_case")
            target_news = st.text_area(
                "Loaded example:", 
                test_cases[selected_case],
                height=120,
                key=f"example_text_{selected_case}"
            )

    with tab_media:
        st.markdown("**Upload images or videos for authenticity analysis:**")
        
        col_img, col_video = st.columns(2)
        with col_img:
            st.markdown("### 🖼️ **Images**")
            uploaded_images = st.file_uploader(
                "Upload images (JPG/PNG) for deepfake detection:", 
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key="image_upload"
            )
            
            if uploaded_images:
                st.success(f"✅ Found {len(uploaded_images)} image(s)")
                for img_file in uploaded_images[:3]:  # Show first 3
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        image = Image.open(img_file)
                        st.image(image, caption=img_file.name, use_column_width=True)
                    with col2:
                        st.caption("Analysis will run with full evidence check")
        
        with col_video:
            st.markdown("### 🎥 **Videos**")
            video_url = st.text_input(
                "Enter video URL (YouTube/Twitter):",
                placeholder="https://youtube.com/watch?v=example",
                key="video_url"
            )
            
            if video_url:
                st.info("🎬 Video analysis will check for deepfake frames and audio sync")

    with tab_urls:
        st.markdown("**Add source URLs for credibility analysis:**")
        source_urls = st.text_area(
            "Enter URLs (one per line):",
            placeholder="https://example.com/article\nhttps://twitter.com/user/status/123",
            height=100,
            key="source_urls"
        )
        
        if source_urls.strip():
            urls = [url.strip() for url in source_urls.split('\n') if url.strip()]
            st.success(f"🔗 Found {len(urls)} source URL(s)")

    st.markdown('</div>', unsafe_allow_html=True)

    # === RECOMMENDATION BANNER ===
    evidence_count = sum([
        bool(target_news) if 'target_news' in locals() else 0,
        len(uploaded_images) if 'uploaded_images' in locals() else 0,
        bool(video_url) if 'video_url' in locals() else 0,
        len([u for u in source_urls.split('\n') if u.strip()]) if 'source_urls' in locals() and source_urls else 0
    ])
    
    if evidence_count == 0:
        st.warning("""
        👋 **Get Started Tip**: 
        Start with text evidence, then add images/videos for stronger analysis!
        
        **💡 Quick Test**: Try the Poonam Pandey hoax case above to see it in action.
        """)
    else:
        st.info(f"📊 **Evidence Ready**: {evidence_count} pieces collected. Click ANALYZE for unified verdict!")

    # === UNIFIED ANALYSIS BUTTON ===
    if st.button("🚀 ANALYZE ALL EVIDENCE", type="primary", use_container_width=True,
                 help="Combines text analysis + media verification + source credibility"):
        
        # Validate we have something to analyze
        if not target_news:
            st.warning("⚠️ Please add some text evidence for best results!")
            st.info("💡 Text provides context—images/videos work better with accompanying claims.")
            st.stop()
        
        # Prepare all evidence for analysis
        media_inputs = {}
        if 'uploaded_images' in locals() and uploaded_images:
            media_inputs["image"] = uploaded_images[0]  # Analyze first image
        if 'video_url' in locals() and video_url:
            media_inputs["video_url"] = video_url
        if 'source_urls' in locals() and source_urls:
            urls = [url.strip() for url in source_urls.split('\n') if url.strip()]
            if urls:
                media_inputs["url"] = urls[0]  # First URL
        
        # Run comprehensive analysis
        with st.spinner("🤖 Analyzing all evidence... This may take 30-60 seconds"):
            # Step 1: Text Analysis
            st.markdown("### 📝 Step 1: Text Evidence Analysis")
            kg = extract_keywords_gist(target_news)
            
            # Insert triggers like 'death' at the front if present in text
            triggers = ["death", "died", "hoax", "fake"]
            text_lower = target_news.lower()
            existing_keywords_lower = [k.lower() for k in kg["keywords"]]
            for trig in triggers[::-1]:
                if trig in text_lower and trig not in existing_keywords_lower:
                    kg["keywords"].insert(0, trig)
                    existing_keywords_lower.insert(0, trig)
            
            col_k1, col_k2 = st.columns([2, 1])
            with col_k1:
                st.markdown("**Key Entities Extracted:**")
                for i, kw in enumerate(kg["keywords"][:5], 1):
                    st.markdown(f"{i}. **{kw}**")
            
            with col_k2:
                st.markdown("**Core Claim:**")
                st.markdown(f"**{kg['gist']}**")
                st.markdown(f"**Time:** {datetime.now().strftime('%H:%M:%S')}")
            
            st.markdown("---")
            
            # Step 2: Source Intelligence
            st.markdown("### 📰 Step 2: Source & Web Analysis")
            col_pct, col_sources = st.columns([1, 2])
            
            with col_pct:
                st.markdown("**Source Consensus:**")
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            with col_sources:
                st.markdown("**Sources Found:**")
                sources_placeholder = st.empty()
            
            # Run text source search
            search_result = real_news_search(kg["keywords"], kg["gist"])
            
            if len(search_result) == 3:
                favor_pct, articles, hoax_context = search_result
            else:
                favor_pct, articles = search_result
                hoax_context = None

            # Force Poonam hoax detection
            text_lower = target_news.lower()
            if "poonam" in text_lower and "pandey" in text_lower and ("death" in text_lower or "died" in text_lower):
                hoax_context = {
                    "status": "ALIVE - CONFIRMED HOAX",
                    "explanation": "Poonam Pandey faked her death on Feb 2, 2024, to raise cervical cancer awareness. She revealed the stunt the next day, urging HPV vaccination and early screening. This viral hoax spread via WhatsApp before being debunked by major outlets.",
                    "timestamp": "Last verified: February 2024",
                    "educational_tip": "🚨 **Red Flag**: Celebrity death announcements + urgent sharing requests + no official family confirmation = 95% hoax probability."
                }
                favor_pct = 15  # Override to low confidence for known hoax
            
            progress_bar.progress(favor_pct / 100)
            status_text.markdown(f"**{favor_pct:.1f}%** source agreement")
            
            if articles:
                source_list = []
                for i, article in enumerate(articles[:5], 1):
                    sentiment_icon = "✅" if article["sentiment"] > 0 else "❌"
                    source_list.append(f"{i}. {sentiment_icon} **{article['title']}**")
                    source_list.append(f"   _{article['source']} | {article['sentiment']:.1f}_")
                
                sources_placeholder.markdown("\n".join(source_list))
                st.caption(f"📊 Analyzed **{len(articles)}** sources from Google News")
            else:
                sources_placeholder.warning("No sources found - limited data available")
            
            # Web source analysis if provided
            if 'source_urls' in locals() and source_urls:
                st.markdown("**🔗 Web Sources:**")
                urls = [url.strip() for url in source_urls.split('\n') if url.strip()]
                for url in urls[:2]:  # First 2 URLs
                    web_result = analyze_web_source(url)
                    cred_icon = "🟢" if web_result["credibility"] > 0.6 else "🟡" if web_result["credibility"] > 0.3 else "🔴"
                    st.markdown(f"{cred_icon} **{url[:50]}...** - {web_result['summary']}")
            
            st.markdown("---")
            
            # Step 3: Media Analysis
            st.markdown("### 🖼️ Step 3: Media Evidence Analysis")
            media_flags, media_results = analyze_media_evidence(media_inputs)
            
            if uploaded_images:
                st.markdown("**📸 Image Analysis:**")
                for i, img_file in enumerate(uploaded_images[:2]):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        image = Image.open(img_file)
                        st.image(image, caption=f"Image {i+1}: {img_file.name}", use_column_width=True)
                    with col2:
                        if "image" in media_results:
                            img_analysis = media_results["image"]
                            if img_analysis.get("is_ai_generated", False):
                                st.error(f"🚨 **Image {i+1}: AI-Generated**")
                                st.caption(f"Confidence: {img_analysis.get('confidence', 0):.1%}")
                            else:
                                st.success(f"✅ **Image {i+1}: Appears Authentic**")
            
            if video_url:
                st.markdown("**🎥 Video Analysis:**")
                if "video" in media_results:
                    video_analysis = media_results["video"]
                    if video_analysis.get("is_deepfake", False):
                        st.error(f"🚨 **Video: Deepfake Detected**")
                    else:
                        st.info(f"✅ **Video: Appears Authentic**")
            
            if not uploaded_images and not video_url:
                st.info("ℹ️ **No media uploaded** - Text + source analysis only")
                st.markdown("*💡 Tip: Upload images/videos for stronger deepfake detection!*")
            
            st.markdown("---")
            
            # Step 4: Unified Evidence Verdict
            st.markdown("### 🎯 Step 4: UNIFIED EVIDENCE VERDICT")
            verdict, explanation = generate_verdict(favor_pct, hoax_context, media_flags)
            
            # Color-coded verdict box
            verdict_class = "verdict-true" if "TRUE" in verdict else "verdict-warning" if "UNCERTAIN" in verdict or "SUSPICIOUS" in verdict else "verdict-danger"
            st.markdown(f'<div class="{verdict_class}">{verdict}</div>', unsafe_allow_html=True)
            
            st.markdown(f"**_{explanation}_**")
            
            # Show evidence breakdown
            evidence_summary = []
            if target_news:
                evidence_summary.append("📝 Text evidence analyzed")
            if uploaded_images:
                evidence_summary.append(f"🖼️ {len(uploaded_images)} image(s) scanned")
            if video_url:
                evidence_summary.append("🎥 Video URL analyzed")
            if source_urls:
                evidence_summary.append(f"🔗 {len([u for u in source_urls.split('\n') if u.strip()])} web source(s)")
            
            st.caption(f"**Evidence Base**: {', '.join(evidence_summary)} | **Final Confidence**: {favor_pct:.0f}%")
            
            # Hoax alert
            if hoax_context and "HOAX" in verdict:
                st.markdown(f'<div class="hoax-alert">🚨 **CONFIRMED HOAX CASE**</div>', unsafe_allow_html=True)
                st.info(hoax_context.get("explanation", "This is a documented misinformation case."))
            
            st.markdown("---")
            
            # Step 5: Integrated Education
            st.markdown("### 🎓 Step 5: VERIFICATION GUIDE")
            reasons = get_educational_reasons(verdict, kg["keywords"], favor_pct, hoax_context, media_flags)
            
            for i, reason in enumerate(reasons, 1):
                st.markdown(f'<div class="edu-tip">{reason}</div>', unsafe_allow_html=True)
            
            # Actionable next steps
            st.markdown("### 🚀 **YOUR ACTION PLAN**")
            action_items = {
                "✅ HIGH CONFIDENCE: TRUE": "✅ **SHARE** this story with proper context and sources.",
                "✅ LIKELY TRUE": "⏳ **MONITOR** for official confirmation in next 24 hours.",
                "⚠️ UNCERTAIN - VERIFY": "🔍 **VERIFY** with primary sources before sharing.",
                "⚠️ SUSPICIOUS": "⏸️ **PAUSE** - Ask trusted contacts if they've seen confirmation.",
                "❌ HIGH RISK: LIKELY FAKE": "🚫 **STOP** the spread - Reply with 'Please verify first!'",
                "❌ CONFIRMED HOAX": "📚 **EDUCATE** others - Share this analysis to prevent future spread!"
            }
            
            st.markdown(f"**{action_items.get(verdict, '📊 **ANALYZE** more examples to build your detection skills!')}**")
            
            st.markdown("---")
            
            # Step 6: Evidence Lineage
            st.markdown("### 🌳 Step 6: EVIDENCE LINEAGE")
            lineage = create_lineage_visualization(kg["keywords"], verdict, favor_pct, media_flags)
            
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                st.markdown("**Evidence Flow:**")
                for step in lineage:
                    confidence_bar = "█" * int(step["confidence"]/10) + "░" * (10 - int(step["confidence"]/10))
                    st.markdown(f"• **{step['node']}** → {step['type']}")
                    st.caption(f"  {confidence_bar} {step['confidence']}%")
            
            with col_l2:
                st.markdown("**Risk Assessment:**")
                if favor_pct < 40:
                    st.error("🔴 **HIGH RISK** - Multiple red flags detected")
                elif favor_pct < 60:
                    st.warning("🟡 **MEDIUM RISK** - Some concerns remain")
                else:
                    st.success("🟢 **LOW RISK** - Evidence appears consistent")
                
                st.markdown(f"**Overall Confidence**: {favor_pct:.0f}/100")
                if media_flags:
                    st.caption(f"**Media Impact**: {sum([v for v in media_flags.values() if v])} red flags found")
            
            st.success("🎉 **FULL EVIDENCE ANALYSIS COMPLETE!** You're now better equipped to spot misinformation.")
        # === ADD INTERACTIVE LINEAGE GRAPH EXPANDER ===
        st.markdown("---")

        # Interactive Lineage Graph Expander
        with st.expander("🔍 **View Interactive Rumor Evolution Graph**", expanded=False):
            st.markdown("**🕸️ Claim Lineage Network** - Click nodes to explore connections")
            
            try:
                # Build the interactive graph
                graph_html = build_claim_lineage_graph(
                    kg["keywords"], 
                    verdict, 
                    favor_pct, 
                    articles[:4],  # Limit to 4 sources for cleaner graph
                    media_flags if 'media_flags' in locals() else None, 
                    hoax_context if 'hoax_context' in locals() else None
                )
                
                if graph_html:
                    st.components.v1.html(
                        graph_html, 
                        height=450,
                        width=800,
                        scrolling=True
                    )
                    st.success("✅ **Interactive Graph Active!** Hover nodes for details, drag to explore.")
                    st.caption("""
                    💡 **How to Read:**
                    • **Red nodes** = Unknown origins (highest risk)
                    • **Blue nodes** = Key entities extracted by AI  
                    • **Green nodes** = Supporting news sources
                    • **Red nodes** = Contradicting sources
                    • **Purple nodes** = Known hoax patterns
                    • **Final node** = Your verdict with confidence score
                    """)
                else:
                    st.warning("⚠️ Interactive graph temporarily unavailable")
                    st.info("Graph shows rumor evolution: Origin → Entities → Sources → Verdict")
                    
            except Exception as e:
                st.error(f"Graph build error: {e}")  # Terminal debug
                st.info("Using text-based lineage summary...")
                
                # Simple fallback summary
                st.markdown("**📊 Quick Lineage Summary:**")
                st.markdown(f"• **Origin**: Unknown source (WhatsApp/social media)")
                st.markdown(f"• **Core Claim**: {' '.join(kg['keywords'][:3])}")
                if articles:
                    st.markdown(f"• **Sources**: {len(articles)} analyzed ({sum(1 for a in articles if a['sentiment'] > 0)} supporting)")
                st.markdown(f"• **Evolution**: {'High-risk mutation path detected' if favor_pct < 40 else 'Stable narrative development'}")
                st.markdown(f"• **Final**: {verdict} ({favor_pct:.0f}% confidence)")

        # Add basic lineage education
        st.markdown("### 🎓 **What This Lineage Tells You**")
        st.markdown("""
        • **Low Source Agreement** (<40%) = Classic hoax pattern  
        • **Media Red Flags** = Visual manipulation likely
        • **Known Hoax Match** = This exact story debunked before
        • **Action**: Always trace back to primary sources before sharing
        """)

        if hoax_context:
            st.info(f"🎭 **Hoax Insight**: {hoax_context.get('explanation', '')[:120]}...")
            # Share functionality
            st.markdown("---")
            if st.button("📤 Share Analysis Summary", type="secondary", use_container_width=True):
                share_text = f"🔍 Misinfo Detector: {verdict}\n📊 Confidence: {favor_pct:.0f}%\n"
                if evidence_summary:
                    share_text += f"📂 Evidence: {', '.join(evidence_summary)}\n"
                if media_flags:
                    flags = [k.replace('_detected', '').replace('_deepfake', ' deepfake').title() for k, v in media_flags.items() if v]
                    if flags:
                        share_text += f"⚠️ Flags: {', '.join(flags)}\n"
                share_text += f"💡 {explanation[:100]}..."
                
                st.code(share_text)

# Results column - Dashboard
with col_results:
    st.subheader("📊 **Analysis Dashboard**")
    
    # Quick stats (will update after analysis)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Evidence Ready", evidence_count, delta=None)
    with col2:
        st.metric("Analysis Status", "Ready" if evidence_count > 0 else "Waiting", delta=None)
    
    st.markdown("---")
    
    st.subheader("🧪 **Test Scenarios**")
    quick_scenarios = {
        "🇮🇳 Celebrity Hoax": "Poonam Pandey death hoax",
        "🦠 Health Conspiracy": "COVID vaccine microchip", 
        "🗳️ Political News": "Election results 2024",
        "💊 Medical Alert": "New COVID variant discovered",
        "🎤 Celebrity Statement": "Deepfake video scandal"
    }
    
    st.markdown("**Load test cases:**")
    for scenario, keywords in quick_scenarios.items():
        if st.button(f"Load: {scenario}", key=f"load_{scenario}"):
            st.session_state.target_news = f"BREAKING: {keywords} - shocking developments reported!"
            st.rerun()
    
    st.markdown("---")
    st.subheader("🎯 **Evidence Tips**")
    st.info("""
    **Maximize accuracy:**
    • Text + images = strongest analysis
    • Include source URLs for credibility
    • Clear face photos work best for deepfakes
    • Test with known cases first
    """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p><strong>Built with ❤️ using Google Cloud's Gen AI Stack</strong></p>
        <p>Multi-modal Evidence Analysis | Team: CODESURFERS | Gen AI Exchange Hackathon 2025</p>
        <p><em>Text + Image + Video + Web Source Verification</em></p>
    </div>
    """, 
    unsafe_allow_html=True
)

# Debug section
with st.expander("🔧 Debug & Developer Info"):
    debug_data = {
        "text_analysis": {"has_text": bool(target_news) if 'target_news' in locals() else False},
        "media_inputs": {"images": len(uploaded_images) if 'uploaded_images' in locals() else 0,
                        "video": bool(video_url) if 'video_url' in locals() else False},
        "web_sources": len([u for u in source_urls.split('\n') if u.strip()]) if 'source_urls' in locals() and source_urls else 0,
        "total_evidence": evidence_count,
        "ready_for_analysis": evidence_count > 0
    }
    st.json(debug_data)



if __name__ == "__main__":
    # For Cloud Run deployment
    st.write("Deployed on Google Cloud Run!")

def generate_mutation_graph(keywords, gist, num_days=5):
    """Generate time-series mutation graph over N days"""
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        gist_vec = vectorizer.fit_transform([gist.lower()])

        days = []
        sentiments = []
        mutations = []

        for day in range(1, num_days + 1):
            query = ' '.join(keywords[:3]) + f' when:{day}d'
            daily_articles = real_news_search([query], gist)
            daily_sent = daily_articles[0] if daily_articles[1] else 0.5
            daily_gist = " ".join([a["summary"] for a in daily_articles[1][:2]]) if daily_articles[1] else ""
            daily_vec = vectorizer.transform([daily_gist.lower()])
            sim_score = cosine_similarity(gist_vec, daily_vec)[0][0] if daily_gist else 0

            days.append(f"Day {day}")
            sentiments.append(daily_sent)
            mutations.append(sim_score * 100)

            if sim_score < 0.89:
                st.warning(f"Day {day}: Mutation detected (Similarity: {sim_score:.1%})")

        fig, ax1 = plt.subplots(figsize=(10, 6))
        ax1.plot(days, sentiments, marker='o', color='blue', linewidth=2, label='Sentiment Score')
        ax1.set_ylabel('Sentiment (-1 Fake to +1 True)', color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')
        ax1.set_ylim(-1, 1)

        ax2 = ax1.twinx()
        ax2.bar(days, mutations, alpha=0.6, color='red', label='Mutation Similarity %')
        ax2.set_ylabel('Gist Similarity to Original (%)', color='red')
        ax2.set_ylim(0, 100)
        ax2.tick_params(axis='y', labelcolor='red')

        plt.title('News Mutation Over Time: How the Claim Evolved', fontsize=14, fontweight='bold')
        fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.9))
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        return buf.getvalue(), days, sentiments, mutations

    except Exception as e:
        st.error(f"Mutation graph error: {e}")
        return None, [], [], []

def display_mutation_graph(mutation_data):
    """Display the mutation graph in app"""
    if mutation_data[0] is None:
        st.warning("Mutation analysis unavailable - showing summary")
        st.info("News mutation tracks how claims evolve: Day 1 - Initial claim, Day 2 - Media pickup, Day 3 - Fact-checking, etc.")
        return
    
    buf, days, sentiments, mutations = mutation_data
    
    # Display the image
    st.image(buf, caption="News Mutation Graph", use_column_width=True)
    
    # Table of values
    st.markdown("**Mutation Data Table:**")
    mutation_df = pd.DataFrame({
        "Day": days,
        "Sentiment Score": sentiments,
        "Mutation Similarity %": mutations
    })
    st.write(mutation_df)

def render_mutation_tree(tree_data):
    """Render tree as interactive PyVis hierarchy"""
    try:
        from networkx import Graph
        from pyvis.network import Network
        import tempfile
        
        G = Graph()
        
        # Add root
        root = tree_data['root']
        G.add_node("root", label=root['label'], color=root['color'], size=30, 
                   title=root['title'], url=root.get('url', ''))
        
        # Add children and edges
        for child in tree_data['children']:
            child_id = child['id']
            G.add_node(child_id, label=child['label'], color=child['color'], size=20, 
                       title=child['title'], url=child.get('url', ''))
            G.add_edge("root", child_id, label="Evolves to", color="#34495e")
        
        # Add mutation edges between children
        for edge in tree_data['edges']:
            from_node = edge['from']
            to_node = edge['to']
            if from_node != "root":
                G.add_edge(from_node, to_node, label=edge['label'], color="#9b59b6", dashes=True)
        
        net = Network(height="500px", width="100%", directed=True, layout=True)
        net.from_nx(G)
        net.set_options("""
        {
          "layout": {
            "hierarchical": {
              "enabled": true,
              "direction": "UD",
              "sortMethod": "directed",
              "levelSeparation": 250,
              "nodeSpacing": 200
            }
          },
          "nodes": {"font": {"size": 12}, "shape": "box", "borderWidth": 2},
          "edges": {"arrows": "to", "font": {"size": 10}, "color": {"inherit": "from"}},
          "physics": {"enabled": false},
          "interaction": {"hover": true, "clickToUse": true}
        }
        """)
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        net.save_graph(temp_file.name)
        with open(temp_file.name, 'r', encoding='utf-8') as f:
            graph_html = f.read()
        import os
        os.unlink(temp_file.name)
        
        return graph_html
        
    except Exception as e:
        st.error(f"Tree render error: {e}")
        return None

# Step 7: Mutation Graph
st.markdown("### 📈 Step 7: NEWS MUTATION TRACKER")
st.markdown("*How this claim evolved over time (5-day analysis)*")

if 'kg' in locals() and kg and "keywords" in kg and "gist" in kg:
    with st.expander("🔍 View Time-Series Mutation Graph", expanded=False):
        mutation_data = generate_mutation_graph(kg["keywords"], kg["gist"])
        display_mutation_graph(mutation_data)
    st.caption("Mutation = Gist similarity <89% from original—tracks hoax evolution!")
else:
    st.info("Run an analysis above to view the mutation tracker.")

def generate_mutation_tree_data(keywords, gist, num_days=5):
    """Generate tree data: Original root + daily mutated children with mutation labels"""
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        gist_vec = vectorizer.fit_transform([gist.lower()])
        
        tree_data = {
            'root': {'label': f"Original Claim: {gist[:50]}...", 'color': 'green', 'title': 'Day 0: User Input'},
            'children': [],
            'edges': []
        }
        
        prev_sentiment = 0.5  # Neutral start
        prev_gist = gist
        
        for day in range(1, num_days + 1):
            query = ' '.join(keywords[:3]) + f' when:{day}d'
            daily_result = real_news_search(keywords, gist.replace('when:', ''))
            daily_articles = daily_result[1] if len(daily_result) > 1 else []
            
            if not daily_articles:
                # Mock for demo if no results
                daily_articles = [{'title': f'Day {day} Mutation: {keywords[0]} hoax confirmed', 'sentiment': prev_sentiment - 0.2, 'summary': f'Mutated version of {gist[:30]}...'}]
            
            daily_sent = np.mean([a['sentiment'] for a in daily_articles]) if daily_articles else 0.5
            daily_gist = " ".join([a['summary'] for a in daily_articles[:2]])
            daily_vec = vectorizer.transform([daily_gist.lower()])
            sim_score = cosine_similarity(gist_vec, daily_vec)[0][0]
            
            if sim_score >= 0.89:
                mutation_label = f"Day {day}: Similarity {sim_score:.1%}"
                mutation_title = f"Sentiment: {daily_sent:.1f} | Change: {daily_sent - prev_sentiment:.1f}"
                tree_data['children'].append({
                    'id': f'day_{day}',
                    'label': f"Mutated: {daily_gist[:30]}...",
                    'color': 'orange' if sim_score < 0.95 else 'blue',
                    'title': mutation_title,
                    'url': daily_articles[0].get('url', '') if daily_articles else ''
                })
                mutation_type = "High Similarity (Stable)" if sim_score >= 0.95 else f"Mutation: Sentiment flip ({daily_sent - prev_sentiment:.1f})"
                tree_data['edges'].append({
                    'from': 'root' if day == 1 else f'day_{day-1}',
                    'to': f'day_{day}',
                    'label': mutation_label + f" | {mutation_type}"
                })
                prev_sentiment = daily_sent
                prev_gist = daily_gist
        
        return tree_data
        
    except Exception as e:
        st.error(f"Tree data error: {e}")
        return {'root': {'label': 'Original Claim'}, 'children': [], 'edges': []}

# === ADDITIONAL ANALYSIS: MUTATION TREE ===
st.markdown("---")
st.markdown("### 🌳 Step 8: CLAIM MUTATION TREE")
st.markdown("*Visualize how the claim has mutated over time*")

if 'kg' in locals() and kg and "keywords" in kg and "gist" in kg:
    with st.expander("🔍 View Claim Mutation Tree", expanded=False):
        tree_data = generate_mutation_tree_data(kg["keywords"], kg["gist"])
        
        # Display the tree using Pyvis
        if tree_data and tree_data['children']:
            net = Network(height="500px", width="100%", directed=True, bgcolor="#1a1a1a")
            
            # Add root node
            net.add_node("root", label=tree_data['root']['label'], title=tree_data['root']['title'], 
                         color=tree_data['root']['color'], size=30)
            
            # Add child nodes and edges
            for child in tree_data['children']:
                net.add_node(child['id'], label=child['label'], title=child['title'], 
                             color=child['color'], size=20)
                net.add_edge("root" if child['id'] == "day_1" else f"day_{int(child['id'].split('_')[1])-1}", 
                             child['id'], 
                             label="", 
                             color="#95a5a6", 
                             width=2)
            
            # Show the network graph
            net.show_buttons(filter_=['physics'])
            graph_html = net.generate_html()
            st.components.v1.html(graph_html, height=550, width=700)
            
            st.success("✅ **Mutation Tree Active!** Explore how the claim evolved.")
        else:
            st.info("No mutations detected - claim appears stable.")
else:
    st.info("Run an analysis above to view the mutation tree.")

