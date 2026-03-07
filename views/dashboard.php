<?php
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}
?><!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#f8fafc;
  --card:#ffffff;
  --border:#e5e7eb;
  --text:#0f172a;
  --primary:#111827;
}
body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,sans-serif}
.nav{background:var(--card);border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center}
.container{padding:2rem;max-width:1200px;margin:0 auto}
.btn{background:var(--primary);color:#fff;padding:.5rem 1rem;border-radius:6px;text-decoration:none}
</style>
</head>
<body>
<nav class="nav">
    <div style="font-weight:600">Ledger App</div>
    <div>
        <span>Welcome, <?= htmlspecialchars($_SESSION['user_name'] ?? 'User') ?></span>
        <a href="/logout" class="btn" style="margin-left:1rem">Logout</a>
    </div>
</nav>
<div class="container">
    <h1>Dashboard</h1>
    <p>You are logged in!</p>
</div>
</body>
</html>
