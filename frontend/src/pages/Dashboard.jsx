import { useOutletContext } from "react-router-dom";

export default function Dashboard() {
  const { user } = useOutletContext();

  return (
    <div className="dashboard">
      <h1>Welcome back, {user.name}</h1>
      <p className="subtitle">
        Cluster: {user.cluster ?? "N/A"} · Risk tolerance: {user.risk_tolerance ?? "N/A"} / 10
      </p>
    </div>
  );
}
