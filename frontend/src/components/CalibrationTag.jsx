export default function CalibrationTag({ status }) {
  return (
    <span className={`tag tag-${status}`}>
      {status === "validated" ? "Validated scoring" : "Scoring calibrating"}
    </span>
  );
}
