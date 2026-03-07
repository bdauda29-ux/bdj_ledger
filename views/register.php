<?php
?><!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Register</title>
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
  --primary:#111827; /* Dark navy/black button */
  --primary-hover:#1f2937;
  --ring:#4f46e5; /* Indigo focus ring */
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,Segoe UI,Roboto,Arial,sans-serif}
.wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}
.card{width:100%;max-width:480px;background:var(--card);border:1px solid var(--border);border-radius:12px;box-shadow:0 8px 30px rgba(15,23,42,.06);padding:1.5rem}
h1{font-size:1.5rem;margin:0 0 1.5rem 0; text-align: center; display: none;} /* Title hidden in image reference, but good for access */
label{display:block;font-size:.9rem;color:var(--text);margin:.75rem 0 .35rem; font-weight: 500;}
input, select{width:100%;padding:.7rem .8rem;border:1px solid var(--border);border-radius:6px;background:#fff;outline:none;transition:border-color .15s, box-shadow .15s; font-family: inherit; font-size: 1rem; color: var(--text);}
input:focus, select:focus{border-color:var(--ring);box-shadow:0 0 0 1px var(--ring)} /* Solid border focus style from image */
.row{display:flex;align-items:center;justify-content:flex-end;gap:.75rem;margin-top:1.5rem}
.footer-row{display:flex;align-items:center;justify-content:flex-end;gap:1rem;margin-top:1.5rem}
.btn{display:inline-flex;align-items:center;justify-content:center;padding:.75rem 1.5rem;background:var(--primary);color:#fff;border:none;border-radius:6px;font-weight:600;cursor:pointer;transition:background-color .15s, transform .02s; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em;}
.btn:hover{background:var(--primary-hover)}
.btn:active{transform:translateY(1px)}
.link{color:var(--muted);text-decoration:underline; font-size: 0.9rem; cursor: pointer;}
.link:hover{color:var(--text)}
/* Specific focus ring matching the image (blue outline) */
input:focus, select:focus {
    border-color: #4f46e5;
    outline: 1px solid #4f46e5;
    box-shadow: none;
}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <form method="post" action="/register">
      <label>Surname</label>
      <input type="text" name="surname" required autofocus>
      
      <label>First Name</label>
      <input type="text" name="first_name" required>
      
      <label>Other Names</label>
      <input type="text" name="other_names">
      
      <label>Passport Number</label>
      <input type="text" name="passport_number">
      
      <label>Passport Expiry Date</label>
      <input type="date" name="passport_expiry" placeholder="mm / dd / yyyy">
      
      <label>Nationality</label>
      <select name="nationality">
        <option value="" disabled selected>Select nationality</option>
        <option value="NG">Nigeria</option>
        <option value="US">United States</option>
        <option value="UK">United Kingdom</option>
        <!-- Add more as needed -->
      </select>
      
      <label>Email</label>
      <input type="email" name="email" required>
      
      <label>Password</label>
      <input type="password" name="password" required>
      
      <label>Confirm Password</label>
      <input type="password" name="confirm_password" required>
      
      <div class="footer-row">
        <a class="link" href="/login">Already registered?</a>
        <button class="btn" type="submit">Register</button>
      </div>
    </form>
  </div>
</div>
</body>
</html>
