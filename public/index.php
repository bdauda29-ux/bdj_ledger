<?php
declare(strict_types=1);
session_start();

require_once __DIR__ . '/../src/AuthController.php';

$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// Simple Router
$auth = new AuthController();

if ($uri === '/' || $uri === '/login' || $uri === '/index.php') {
    $auth->login();
} elseif ($uri === '/signup') {
    $auth->signup();
} elseif ($uri === '/logout') {
    $auth->logout();
} elseif ($uri === '/dashboard') {
    if (!isset($_SESSION['user_id'])) {
        header('Location: /login');
        exit;
    }
    require __DIR__ . '/../views/dashboard.php';
} else {
    // Basic 404
    http_response_code(404);
    echo "<h1>404 Not Found</h1><p>The page you requested could not be found.</p><a href='/'>Go Home</a>";
}
