import { useState } from "react";

const SECTIONS = [
  {
    title: "General",
    items: [
      ["What is Reelfit?",
       "Reelfit scores your film against a festival's actual selection history before you pay a submission fee, and gives festivals consistent AI-assisted judging with honest analytics. One flat fee scores a film against every listed festival."],
      ["Do I give up any rights to my work?",
       "No. Reelfit never takes rights, never acts as a distributor or sales agent, and never shares your contact details. Festivals reach you only through a relay address you can revoke at any time."],
      ["What does “validated” vs “calibrating” mean on a score?",
       "Every fit score is labeled with how much history stands behind it. Validated festivals have enough confirmed selection outcomes for the score to be reliable; calibrating festivals are still building that history, so treat their scores as directional."],
      ["Does Reelfit accept screenplays?",
       "Yes — add a screenplay project to your library and you'll see festivals with script categories. Runtime rules only apply to finished films."],
    ],
  },
  {
    title: "For filmmakers",
    items: [
      ["How do fit scores work?",
       "One credit scores one film against every listed festival at once. The score estimates how closely your film matches what each festival has actually selected before — genre affinity, runtime fit, and recency. A low score isn't a failure; it's information that saves you a fee."],
      ["Where can I find discounts and entry fee waivers?",
       "Festivals issue their own promo codes — enter them at checkout. Codes can discount the fee, waive it entirely, or allow late entry after the final deadline."],
      ["How do reviews work?",
       "Only filmmakers with a real submission to a festival can review it, and every review is tied to that submission record. Festivals can reply publicly."],
      ["What happens when my film is selected?",
       "You're notified immediately, your laurel is ready to download from your dashboard, and your score-versus-outcome history builds so future recommendations get sharper."],
    ],
  },
  {
    title: "For festivals",
    items: [
      ["How does judging work?",
       "Add staff by email as programmers, jury members or viewers. Configure a scoring rubric (or use the standard film judging form), assign entries to judges, and track everyone's progress in Judging Insights. Every status change is logged and automatically notifies the filmmaker."],
      ["What analytics do I get?",
       "Real conversion analytics: page views by traffic source, submissions, conversion rates and fees — computed from actual platform records, never self-reported. Plus reports and spreadsheet exports."],
      ["How does my festival reach “validated” scoring?",
       "Add your past selection outcomes when onboarding. Once enough confirmed history is in (about 30 outcomes), your scores are labeled validated — filmmakers see that label on every score, so more history means more trust."],
      ["Can I contact submitters directly?",
       "You can message all submitters at once from your dashboard, and reach individuals through their relay address. Raw emails are never exposed — filmmakers control their contact and can revoke it."],
    ],
  },
];

function Item({ q, a }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        className="btn btn-quiet"
        style={{ padding: "12px 0", textAlign: "left", width: "100%", justifyContent: "flex-start", fontWeight: 600 }}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {open ? "− " : "+ "}{q}
      </button>
      {open && <p style={{ marginTop: 0 }}>{a}</p>}
    </div>
  );
}

export default function Help() {
  return (
    <>
      <div className="hero">
        <h1>Help center</h1>
        <p className="lede">Plain answers about how Reelfit works.</p>
      </div>
      {SECTIONS.map((section) => (
        <div className="card" key={section.title}>
          <h2>{section.title}</h2>
          <div className="list-divided">
            {section.items.map(([q, a]) => (
              <Item key={q} q={q} a={a} />
            ))}
          </div>
        </div>
      ))}
      <p className="muted">
        Something else? Write to us — hello@reelfit.example.com
      </p>
    </>
  );
}
