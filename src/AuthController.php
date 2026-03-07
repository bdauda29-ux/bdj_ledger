<?php
declare(strict_types=1);

require_once __DIR__ . '/User.php';

class AuthController {
    public function login() {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $email = $_POST['email'] ?? '';
            $password = $_POST['password'] ?? '';
            
            $userModel = new User();
            $user = $userModel->findByEmail($email);
            
            if ($user && password_verify($password, $user['password'])) {
                $_SESSION['user_id'] = $user['id'];
                $_SESSION['user_name'] = $user['name'];
                header('Location: /dashboard');
                exit;
            } else {
                $error = "Invalid credentials";
                require __DIR__ . '/../views/login.php';
            }
        } else {
            require __DIR__ . '/../views/login.php';
        }
    }

    public function signup() {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $name = $_POST['name'] ?? '';
            $email = $_POST['email'] ?? '';
            $password = $_POST['password'] ?? '';
            
            if (empty($name) || empty($email) || empty($password)) {
                $error = "All fields are required";
                require __DIR__ . '/../views/signup.php';
                return;
            }

            $userModel = new User();
            if ($userModel->findByEmail($email)) {
                 $error = "Email already exists";
                 require __DIR__ . '/../views/signup.php';
                 return;
            }

            if ($userModel->create($name, $email, $password)) {
                header('Location: /login');
                exit;
            } else {
                $error = "Registration failed";
                require __DIR__ . '/../views/signup.php';
            }
        } else {
            require __DIR__ . '/../views/signup.php';
        }
    }

    public function logout() {
        session_destroy();
        header('Location: /login');
        exit;
    }
}
