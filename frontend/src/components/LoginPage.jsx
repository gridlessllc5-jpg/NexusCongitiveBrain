import React, { useState } from "react";
import axios from "axios";
import { User, Lock, Mail, LogIn, UserPlus, Loader2, AlertCircle } from "lucide-react";
import "./LoginPage.css";

const LoginPage = ({ API, onLogin }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Form fields
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [email, setEmail] = useState("");
  const [playerName, setPlayerName] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!isLogin && password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setLoading(true);

    try {
      let response;
      if (isLogin) {
        response = await axios.post(`${API}/auth/login`, {
          username,
          password
        });
      } else {
        response = await axios.post(`${API}/auth/register`, {
          username,
          password,
          email: email || undefined,
          player_name: playerName || username
        });
      }

      if (response.data.success) {
        // Store token
        localStorage.setItem("auth_token", response.data.token);
        localStorage.setItem("user_data", JSON.stringify({
          user_id: response.data.user_id,
          username: response.data.username,
          player_name: response.data.player_name
        }));
        
        onLogin(response.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* Background Effects */}
      <div className="bg-scratches"></div>
      <div className="bg-vignette"></div>
      
      {/* Main Content */}
      <div className="login-container">
        {/* Logo */}
        <div className="logo-container">
          <img 
            src="/assets/logo.jpg" 
            alt="Fractured Survival" 
            className="game-logo"
          />
        </div>

        {/* Auth Card */}
        <div className="auth-card">
          {/* Tabs */}
          <div className="auth-tabs">
            <button
              className={`auth-tab ${isLogin ? 'active' : ''}`}
              onClick={() => { setIsLogin(true); setError(null); }}
              data-testid="login-tab"
            >
              <LogIn size={18} />
              <span>LOGIN</span>
            </button>
            <button
              className={`auth-tab ${!isLogin ? 'active' : ''}`}
              onClick={() => { setIsLogin(false); setError(null); }}
              data-testid="register-tab"
            >
              <UserPlus size={18} />
              <span>REGISTER</span>
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="auth-form">
            {error && (
              <div className="auth-error" data-testid="auth-error">
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
            )}

            <div className="form-group">
              <label>
                <User size={16} />
                <span>Username</span>
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
                disabled={loading}
                autoComplete="username"
                data-testid="username-input"
              />
            </div>

            {!isLogin && (
              <div className="form-group">
                <label>
                  <Mail size={16} />
                  <span>Email (optional)</span>
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  disabled={loading}
                  autoComplete="email"
                  data-testid="email-input"
                />
              </div>
            )}

            {!isLogin && (
              <div className="form-group">
                <label>
                  <User size={16} />
                  <span>Player Name</span>
                </label>
                <input
                  type="text"
                  value={playerName}
                  onChange={(e) => setPlayerName(e.target.value)}
                  placeholder="Your in-game display name"
                  disabled={loading}
                  data-testid="player-name-input"
                />
              </div>
            )}

            <div className="form-group">
              <label>
                <Lock size={16} />
                <span>Password</span>
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                disabled={loading}
                autoComplete={isLogin ? "current-password" : "new-password"}
                data-testid="password-input"
              />
            </div>

            {!isLogin && (
              <div className="form-group">
                <label>
                  <Lock size={16} />
                  <span>Confirm Password</span>
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm your password"
                  required
                  disabled={loading}
                  autoComplete="new-password"
                  data-testid="confirm-password-input"
                />
              </div>
            )}

            <button 
              type="submit" 
              className="auth-submit-btn"
              disabled={loading}
              data-testid="auth-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="spinning" size={20} />
                  <span>{isLogin ? 'LOGGING IN...' : 'CREATING ACCOUNT...'}</span>
                </>
              ) : (
                <>
                  {isLogin ? <LogIn size={20} /> : <UserPlus size={20} />}
                  <span>{isLogin ? 'ENTER THE WASTELAND' : 'JOIN THE SURVIVORS'}</span>
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="auth-footer">
            <p>NPC Intelligence System v1.0</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
