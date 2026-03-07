<?php
declare(strict_types=1);

session_start();

$uri = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

// Basic routing
switch ($uri) {
    case '/':
    case '/login':
        require __DIR__ . '/../views/login.php';
        break;
        
    case '/register':
        require __DIR__ . '/../views/register.php';
        break;
        
    default:
        http_response_code(404);
        echo "404 Not Found";
        break;
}
