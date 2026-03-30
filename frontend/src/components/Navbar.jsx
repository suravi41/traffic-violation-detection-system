import { Link, useNavigate } from "react-router-dom";

export default function Navbar() {

  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  return (
    <div className="navbar">

      <div className="brand brand-wrap">
        <img src="/LOGO.jpg" alt="Logo" className="logo" />
        <span>Traffic Monitoring</span>
      </div>

      <div className="nav-links">

        <Link to="/home">Home</Link>
        <Link to="/upload">Upload</Link>
        <Link to="/evidence">Evidence</Link>
        <Link to="/profile">Profile</Link>

        <button className="logout-btn" onClick={handleLogout}>
          Logout
        </button>

      </div>

    </div>
  );
}