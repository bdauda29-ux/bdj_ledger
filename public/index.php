<?php
declare(strict_types=1);

session_start();

$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// 1. Redirect root URL to /login
if ($uri === '/') {
    header('Location: /login');
    exit;
}

// 2. Handle Login Route
if ($uri === '/login') {
    require __DIR__ . '/../views/login.php';
    exit;
}

// 3. Handle Register Route
if ($uri === '/register') {
    require __DIR__ . '/../views/register.php';
    exit;
}

// 4. Global Auth Check / Default Fallback
// If the user is trying to access any other route and is NOT logged in, redirect to /login.
// This ensures the login page is the default for any out-of-session access.
if (!isset($_SESSION['user_id'])) {
    header('Location: /login');
    exit;
}

// 5. Placeholder for authenticated 404s (or dashboard in the future)
http_response_code(404);
echo "404 Not Found";
