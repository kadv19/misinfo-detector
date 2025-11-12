import React, { useState } from "react";
import {
  FaEye,
  FaEyeSlash,
  FaCopy,
  FaSync,
  FaTrash,
  FaPlus,
  FaHome,
  FaKey,
  FaCheck,
  FaTimes,
} from "react-icons/fa";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import ProductionPageBg from "../assets/CheckPoint/ProductionPage.png";

export default function ProductionPage() {
  const navigate = useNavigate();
  const [animating, setAnimating] = useState(false);

  const [prodKeyVisible, setProdKeyVisible] = useState(false);
  const [devKeyVisible, setDevKeyVisible] = useState(false);
  const [prodKey, setProdKey] = useState(
    "cp_prod_sk_1a2b3c4d5e6f7g8h9ieurhgiunergiunergoindfoj"
  );
  const [devKey, setDevKey] = useState(
    "cp_dev_sk_9x8y7z6w5v4u3t2s1r0qwertyuiopasdfghjkl"
  );
  const [copiedProdKey, setCopiedProdKey] = useState(false);
  const [copiedDevKey, setCopiedDevKey] = useState(false);
  const [copiedIntegration, setCopiedIntegration] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyType, setNewKeyType] = useState("Production");
  const [generatedKeys, setGeneratedKeys] = useState([]);
  const [generatedKeysVisibility, setGeneratedKeysVisibility] = useState({});
  const [copiedGeneratedKeys, setCopiedGeneratedKeys] = useState({});

  const copyToClipboard = (text, setCopiedState) => {
    navigator.clipboard.writeText(text);
    setCopiedState(true);
    setTimeout(() => setCopiedState(false), 1000);
  };

  const generateApiKey = (prefix = "cp_sk_") => {
    return prefix + Math.random().toString(36).substring(2, 18);
  };

  const handleCreateKey = () => {
    const newKey = generateApiKey(
      newKeyType === "Production" ? "cp_prod_sk_" : "cp_dev_sk_"
    );
    const keyId = Date.now();
    setGeneratedKeys([
      ...generatedKeys,
      { id: keyId, name: newKeyName, key: newKey, type: newKeyType },
    ]);
    setGeneratedKeysVisibility({ ...generatedKeysVisibility, [keyId]: false });
    setModalOpen(false);
    setNewKeyName("");
    setNewKeyType("Production");
  };

  const toggleGeneratedKeyVisibility = (keyId) => {
    setGeneratedKeysVisibility({
      ...generatedKeysVisibility,
      [keyId]: !generatedKeysVisibility[keyId],
    });
  };

  const copyGeneratedKey = (keyId, text) => {
    navigator.clipboard.writeText(text);
    setCopiedGeneratedKeys({ ...copiedGeneratedKeys, [keyId]: true });
    setTimeout(() => {
      setCopiedGeneratedKeys({ ...copiedGeneratedKeys, [keyId]: false });
    }, 1000);
  };

  const handleDeleteGeneratedKey = (keyId) => {
    setGeneratedKeys(generatedKeys.filter((key) => key.id !== keyId));
    const newVisibility = { ...generatedKeysVisibility };
    delete newVisibility[keyId];
    setGeneratedKeysVisibility(newVisibility);

    const newCopied = { ...copiedGeneratedKeys };
    delete newCopied[keyId];
    setCopiedGeneratedKeys(newCopied);
  };

  const handleDeleteProdKey = () => {
    setProdKey("");
    setProdKeyVisible(false);
  };

  const handleDeleteDevKey = () => {
    setDevKey("");
    setDevKeyVisible(false);
  };

  const handleGoHome = () => {
    setAnimating(true);
    setTimeout(() => navigate("/"), 300); // match animation duration
  };

  const cardClass =
    "w-full max-w-7xl bg-white/20 backdrop-blur-lg border border-white/30 rounded-3xl shadow-lg p-6 flex flex-col gap-4 transition-all duration-300 ease-in-out hover:scale-105 hover:shadow-2xl hover:bg-white/25";
  const buttonClass =
    "flex items-center gap-2 bg-white/20 border border-white/30 text-white font-semibold px-4 py-2 rounded-2xl transition-all duration-300 ease-in-out hover:scale-105 hover:shadow-xl hover:bg-white/30";
  const copyButtonClass =
    "bg-white/10 p-3 rounded-xl transition-all duration-300 ease-in-out hover:scale-110 hover:bg-white/20";

  return (
    <AnimatePresence>
      {!animating && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
          className="relative min-h-screen flex flex-col font-piazzolla text-white"
        >
          {/* Background */}
          <div
            className="absolute inset-0 bg-cover bg-center bg-no-repeat"
            style={{ backgroundImage: `url(${ProductionPageBg})` }}
          />

          {/* Home Button */}
          <button
            onClick={handleGoHome}
            className="absolute top-6 left-6 z-30 text-white text-xl bg-white/20 backdrop-blur-sm p-3 rounded-full hover:bg-white/30 transition shadow-lg"
          >
            <FaHome />
          </button>

          {/* Main Content */}
          <div className="relative z-10 flex flex-col items-center justify-start px-6 py-20 gap-10 flex-1">
            {/* Header Card */}
            <motion.div
              initial={{ opacity: 0, y: -40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className={`${cardClass} flex items-center justify-between`}
            >
              <div className="flex items-center gap-4">
                <FaKey className="text-3xl text-orange-400 drop-shadow-md" />
                <h1 className="text-2xl font-bold text-white">API Key Management</h1>
              </div>
              <button className={buttonClass} onClick={() => setModalOpen(true)}>
                <FaPlus /> Create New Key
              </button>
            </motion.div>

            {/* Production API Key Card */}
            <motion.div
              initial={{ opacity: 0, x: -50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.7 }}
              className={cardClass}
            >
              <h2 className="text-lg font-semibold text-orange-300">
                Production API Key
              </h2>
              <div className="flex items-center gap-3">
                <input
                  type={prodKeyVisible ? "text" : "password"}
                  value={prodKey}
                  readOnly
                  className="flex-1 bg-white/10 text-white p-3 rounded-xl outline-none border border-white/20 font-mono text-sm"
                />
                <button
                  onClick={() => setProdKeyVisible(!prodKeyVisible)}
                  className="bg-white/10 p-3 rounded-xl hover:bg-white/20 transition"
                >
                  {prodKeyVisible ? <FaEyeSlash /> : <FaEye />}
                </button>
                <button
                  onClick={() => copyToClipboard(prodKey, setCopiedProdKey)}
                  className={copyButtonClass}
                >
                  {copiedProdKey ? <FaCheck className="text-white" /> : <FaCopy />}
                </button>
                <button
                  onClick={() => setProdKey(generateApiKey("cp_prod_sk_"))}
                  className="bg-white/10 p-3 rounded-xl hover:bg-white/20 transition"
                >
                  <FaSync />
                </button>
                <button
                  onClick={handleDeleteProdKey}
                  className="bg-white/10 p-3 rounded-xl hover:bg-white/20 transition text-red-400"
                >
                  <FaTrash />
                </button>
              </div>
            </motion.div>

            {/* Development API Key Card */}
            <motion.div
              initial={{ opacity: 0, x: 50 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.7 }}
              className={cardClass}
            >
              <h2 className="text-lg font-semibold text-orange-300">
                Development API Key
              </h2>
              <div className="flex items-center gap-3">
                <input
                  type={devKeyVisible ? "text" : "password"}
                  value={devKey}
                  readOnly
                  className="flex-1 bg-white/10 text-white p-3 rounded-xl outline-none border border-white/20 font-mono text-sm"
                />
                <button
                  onClick={() => setDevKeyVisible(!devKeyVisible)}
                  className="bg-white/10 p-3 rounded-xl hover:bg-white/20 transition"
                >
                  {devKeyVisible ? <FaEyeSlash /> : <FaEye />}
                </button>
                <button
                  onClick={() => copyToClipboard(devKey, setCopiedDevKey)}
                  className={copyButtonClass}
                >
                  {copiedDevKey ? <FaCheck className="text-white" /> : <FaCopy />}
                </button>
                <button
                  onClick={() => setDevKey(generateApiKey("cp_dev_sk_"))}
                  className="bg-white/10 p-3 rounded-xl hover:bg-white/20 transition"
                >
                  <FaSync />
                </button>
                <button
                  onClick={handleDeleteDevKey}
                  className="bg-white/10 p-3 rounded-xl hover:bg-white/20 transition text-red-400"
                >
                  <FaTrash />
                </button>
              </div>
            </motion.div>

            {/* Generated Keys List */}
            {generatedKeys.map((keyItem) => (
              <motion.div
                key={keyItem.id}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
                className={cardClass}
              >
                <h2 className="text-lg font-semibold text-orange-300">
                  {keyItem.name} ({keyItem.type})
                </h2>
                <div className="flex items-center gap-3">
                  <input
                    type={generatedKeysVisibility[keyItem.id] ? "text" : "password"}
                    value={keyItem.key}
                    readOnly
                    className="flex-1 bg-white/10 text-white p-3 rounded-xl outline-none border border-white/20 font-mono text-sm"
                  />
                  <button
                    onClick={() => toggleGeneratedKeyVisibility(keyItem.id)}
                    className="bg-white/10 p-3 rounded-xl hover:bg-white/20 transition"
                  >
                    {generatedKeysVisibility[keyItem.id] ? <FaEyeSlash /> : <FaEye />}
                  </button>
                  <button
                    onClick={() => copyGeneratedKey(keyItem.id, keyItem.key)}
                    className={copyButtonClass}
                  >
                    {copiedGeneratedKeys[keyItem.id] ? (
                      <FaCheck className="text-white" />
                    ) : (
                      <FaCopy />
                    )}
                  </button>
                  <button
                    onClick={() => handleDeleteGeneratedKey(keyItem.id)}
                    className="bg-white/10 p-3 rounded-xl hover:bg-white/20 transition text-red-400"
                  >
                    <FaTrash />
                  </button>
                </div>
              </motion.div>
            ))}

            {/* Integration Instructions Card */}
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7 }}
              className={cardClass}
            >
              <h2 className="text-lg font-semibold text-orange-300">
                Integration Instructions
              </h2>
              <h3 className="text-md font-medium flex items-center justify-between text-black">
                Authentication Example
                <button
                  onClick={() =>
                    copyToClipboard(
                      `curl -X POST https://api.checkpoint.com/v1/analyze\n-H "Authorization: Bearer YOUR_API_KEY"\n-H "Content-Type: application/json"\n-d '{"content": "..."}'`,
                      setCopiedIntegration
                    )
                  }
                  className="bg-white/10 p-3 rounded-xl transition-all duration-300 hover:bg-white/20 hover:scale-110 text-white"
                >
                  {copiedIntegration ? <FaCheck className="text-white" /> : <FaCopy />}
                </button>
              </h3>
              <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl p-4 font-mono text-sm leading-relaxed text-black whitespace-pre-wrap">
                {`curl -X POST https://api.checkpoint.com/v1/analyze
-H "Authorization: Bearer YOUR_API_KEY"
-H "Content-Type: application/json"
-d '{"content": "..."}'`}
              </div>
              <p className="text-xs text-black opacity-80">
                Include your API key in the{" "}
                <span className="font-semibold">Authorization</span> header using the
                Bearer format.
              </p>
            </motion.div>
          </div>

         <footer className="relative z-10 bg-white/10 backdrop-blur-lg border border-white/20 rounded-t-3xl shadow-md text-white py-6 px-8 mt-auto w-full">
  <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
    <div className="text-center md:text-left">
      <h3 className="font-bold text-lg mb-1">CheckPoint</h3>
      <p className="text-sm opacity-80">
        Verifying truth in the digital world, providing transparency and
        reliability.
      </p>
    </div>
    <div className="text-center md:text-right text-xs opacity-70">
      &copy; 2025 CheckPoint. All rights reserved.
    </div>
  </div>
</footer>


          {/* Modal */}
          <AnimatePresence>
            {modalOpen && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
                onClick={() => setModalOpen(false)}
              >
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  exit={{ scale: 0.8, opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 max-w-md w-full text-white flex flex-col gap-4 border border-white/30"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex justify-between items-center">
                    <h2 className="text-xl font-bold">Create New API Key</h2>
                    <button
                      onClick={() => setModalOpen(false)}
                      className="text-white text-xl hover:scale-110 transition"
                    >
                      <FaTimes />
                    </button>
                  </div>
                  <input
                    type="text"
                    placeholder="Key Name"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    className="p-3 rounded-xl bg-white/10 border border-white/30 outline-none text-black placeholder-black/60"
                  />
                  <select
                    value={newKeyType}
                    onChange={(e) => setNewKeyType(e.target.value)}
                    className="p-3 rounded-xl bg-white/10 border border-white/30 outline-none text-black"
                  >
                    <option>Production</option>
                    <option>Development</option>
                  </select>
                  <button
                    onClick={handleCreateKey}
                    disabled={!newKeyName.trim()}
                    className="mt-2 bg-orange-400 text-white p-3 rounded-2xl font-semibold hover:bg-orange-300 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Generate Key
                  </button>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
