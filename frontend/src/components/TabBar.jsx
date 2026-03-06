export default function TabBar({ tabs, active, onSelect }) {
  return (
    <div className="tab-bar">
      <div className="tab-bar-left">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={`tab-btn${active === tab ? " active" : ""}`}
            onClick={() => onSelect(tab)}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="tab-bar-logo">
        <img src="/every-logo.svg" alt="Every" height="20" />
      </div>
    </div>
  );
}
