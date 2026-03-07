<?php
?><!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#f8fafc;
  --card:#ffffff;
  --border:#e5e7eb;
  --text:#0f172a;
  --muted:#475569;
  --primary:#111827;
  --primary-hover:#1f2937;
  --ring:#4f46e5;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,Segoe UI,Roboto,Arial,sans-serif}
.wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}
.card{width:100%;max-width:460px;background:var(--card);border:1px solid var(--border);border-radius:12px;box-shadow:0 8px 30px rgba(15,23,42,.06);padding:1.25rem}
h1{font-size:1.25rem;margin:0 0 .75rem 0}
label{display:block;font-size:.9rem;color:var(--muted);margin:.5rem 0 .35rem}
input{width:100%;padding:.7rem .8rem;border:1px solid var(--border);border-radius:10px;background:#fff;outline:none;transition:border-color .15s, box-shadow .15s}
input:focus{border-color:var(--ring);box-shadow:0 0 0 3px rgba(79,70,229,.25)}
.row{display:flex;align-items:center;justify-content:space-between;gap:.75rem;margin-top:1rem}
.btn{display:inline-flex;align-items:center;justify-content:center;padding:.7rem 1rem;background:var(--primary);color:#fff;border:none;border-radius:10px;font-weight:600;cursor:pointer;transition:background-color .15s, transform .02s}
.btn:hover{background:var(--primary-hover)}
.btn:active{transform:translateY(1px)}
.link{color:#4f46e5;text-decoration:none}
.link:hover{text-decoration:underline}
.hint{margin-top:.75rem;color:var(--muted);font-size:.9rem}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>Login</h1>
    <form method="post" action="/login">
      <label>Email</label>
      <input type="email" name="email" required>
      <label>Password</label>
      <input type="password" name="password" required>
      <div class="row">
        <a class="link" href="/register">Create account</a>
        <button class="btn" type="submit">Sign in</button>
      </div>
    </form>
    <div class="hint">Already registered? Use your email and password.</div>
  </div>
</div>
</body>
</html>

