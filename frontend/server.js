const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");
const path = require("path");

const app = express();
const apiTarget = process.env.VITE_API_URL || "http://localhost:8000";

app.use("/api", createProxyMiddleware({ target: apiTarget, changeOrigin: true }));
app.use(express.static(path.join(__dirname, "dist")));
app.get("*", (req, res) => res.sendFile(path.join(__dirname, "dist", "index.html")));
app.listen(3000, () => console.log("Frontend on http://localhost:3000"));
