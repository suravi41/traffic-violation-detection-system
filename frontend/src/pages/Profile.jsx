import Navbar from "../components/Navbar";

export default function Profile() {
  return (
    <div className="page">
      <Navbar />
      <div className="container">
        <div className="card">
          <h1 className="section-title">Officer Profile</h1>
          <p className="muted">Traffic monitoring officer dashboard</p>
        </div>
      </div>
    </div>
  );
}