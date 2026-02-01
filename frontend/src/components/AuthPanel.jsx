import React, { useState } from "react";
import axios from "axios";
import { User, Lock, Mail, LogIn, UserPlus, Loader2 } from "lucide-react";

const AuthPanel = ({ API, onLogin, onLogout, currentUser }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Form fields
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [playerName, setPlayerName] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
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
        
        // Clear form
        setUsername("");
        setPassword("");
        setEmail("");
        setPlayerName("");
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");
    onLogout();
  };

  // If user is logged in, show profile
  if (currentUser) {
    return (
      <div className="auth-panel logged-in" data-testid="auth-panel-logged-in">
        <div className="user-profile">
          <div className="user-avatar">
            <User size={32} />
          </div>
          <div className="user-info">
            <span className="user-player-name">{currentUser.player_name}</span>
            <span className="user-username">@{currentUser.username}</span>
          </div>
        </div>
        <button 
          className="logout-btn" 
          onClick={handleLogout}
          data-testid="logout-btn"
        >
          Logout
        </button>
      </div>
    );
  }

  return (
    <div className="auth-panel" data-testid="auth-panel">
      <div className="auth-tabs">
        <button
          className={`auth-tab ${isLogin ? 'active' : ''}`}
          onClick={() => setIsLogin(true)}
          data-testid="login-tab"
        >
          <LogIn size={16} /> Login
        </button>
        <button
          className={`auth-tab ${!isLogin ? 'active' : ''}`}
          onClick={() => setIsLogin(false)}
          data-testid="register-tab"
        >
          <UserPlus size={16} /> Register
        </button>
      </div>

      <form onSubmit={handleSubmit} className="auth-form" data-testid="auth-form">
        {error && (
          <div className="auth-error" data-testid="auth-error">
            {error}
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
            placeholder="Enter username"
            required
            disabled={loading}
            data-testid="username-input"
          />
        </div>

        <div className="form-group">
          <label>
            <Lock size={16} />
            <span>Password</span>
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
            required
            disabled={loading}
            data-testid="password-input"
          />
        </div>

        {!isLogin && (
          <>
            <div className="form-group">
              <label>
                <Mail size={16} />
                <span>Email (optional)</span>
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter email"
                disabled={loading}
                data-testid="email-input"
              />
            </div>

            <div className="form-group">
              <label>
                <User size={16} />
                <span>Player Name (display name)</span>
              </label>
              <input
                type="text"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                placeholder="Enter player name"
                disabled={loading}
                data-testid="player-name-input"
              />
            </div>
          </>
        )}

        <button 
          type="submit" 
          className="auth-submit-btn"
          disabled={loading}
          data-testid="auth-submit-btn"
        >
          {loading ? (
            <>
              <Loader2 className="spinning" size={16} />
              <span>{isLogin ? 'Logging in...' : 'Registering...'}</span>
            </>
          ) : (
            <>
              {isLogin ? <LogIn size={16} /> : <UserPlus size={16} />}
              <span>{isLogin ? 'Login' : 'Create Account'}</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};

export default AuthPanel;
