export default function SectionCard({ title, children }) {
  return (
    <section className="sidebar-card">
      <h3>{title}</h3>
      {children}
    </section>
  );
}
