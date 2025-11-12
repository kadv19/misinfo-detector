import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App"; // Import the App component
import './index.css'; // <-- Import CSS here

const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
