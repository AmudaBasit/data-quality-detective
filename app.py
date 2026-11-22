"""Explore before-and-after quality, cleaning decisions, and modeling risks."""
import pandas as pd
import streamlit as st

from audit import ROOT, load, metrics, privacy, problems, readiness

DATA = ROOT / "data"
st.set_page_config(page_title="Data Quality Detective", page_icon="🔎", layout="wide")


@st.cache_data
def load_case():
    return tuple(load(DATA / name) for name in (
        "retail_raw.csv", "retail_clean.csv", "cleaning_log.csv", "defect_manifest.csv"
    ))


raw, cleaned, decisions, manifest = load_case()
before, after = metrics(raw), metrics(cleaned)

st.title("Data Quality Detective")
st.write("Trace defects in synthetic retail transactions, review the cleaning decisions, and check whether the resulting data is ready for a return prediction experiment.")

overview, evidence, model, release = st.tabs(
    ["Quality overview", "Inspect records", "ML readiness", "Privacy and downloads"]
)
with overview:
    cards = st.columns(4)
    cards[0].metric("Source records", f"{len(raw):,}")
    cards[1].metric("Clean records", f"{len(cleaned):,}", f"{len(cleaned)-len(raw):,}",
                    delta_color="off")
    cards[2].metric("Rows passing all rules", f"{after['passing_pct']:.1f}%",
                    f"{after['passing_pct']-before['passing_pct']:+.1f} pp")
    cards[3].metric("Quarantined", int(decisions.action.eq("quarantined").sum()))
    st.caption("Pass rates use each dataset's own row count. Removal and repair both affect the rate.")

    st.subheader("Rule violations")
    comparison = pd.DataFrame({"Raw": before["rule_counts"], "Clean": after["rule_counts"]})
    signal = comparison.loc[comparison.sum(axis=1).gt(0)]
    st.bar_chart(signal, horizontal=True, stack=False, color=["#bd6332", "#087f75"])
    with st.expander("Show all rule counts"):
        st.dataframe(comparison)
    left, right = st.columns(2)
    with left:
        st.subheader("Missing cells by field")
        st.dataframe(pd.DataFrame({"Raw": before["missing_cells"], "Clean": after["missing_cells"]}))
    with right:
        st.subheader("Price outliers")
        st.dataframe(pd.DataFrame({
            "Raw": [before["rule_counts"]["Invalid unit price"], before["price_iqr_outliers"]],
            "Clean": [after["rule_counts"]["Invalid unit price"], after["price_iqr_outliers"]],
        }, index=["Invalid by price rule", "Flagged by 1.5 × IQR"]))
        st.caption("The price rule accepts USD 0.01–500. IQR fences are calculated separately for each dataset from its finite numeric prices.")

with evidence:
    st.subheader("Transaction explorer")
    stage = st.radio("Dataset", ["Raw", "Clean"], horizontal=True)
    frame = raw if stage == "Raw" else cleaned
    flags = problems(frame)
    rule = st.selectbox("Quality filter", ["All rows", "Any violation", *flags.columns])
    selected = frame
    if rule == "Any violation":
        selected = frame.loc[flags.any(axis=1)]
    elif rule != "All rows":
        selected = frame.loc[flags[rule]]
    query = st.text_input("Find transaction ID").strip()
    if query:
        selected = selected.loc[selected.transaction_id.str.contains(query, case=False, regex=False)]
    st.caption(f"{len(selected):,} matching records")
    st.dataframe(selected, hide_index=True)

    st.subheader("Cleaning decisions")
    actions = st.multiselect("Action filter", sorted(decisions.action.unique()))
    row_log = decisions.loc[decisions.action.isin(actions)] if actions else decisions
    st.dataframe(row_log, hide_index=True)
    with st.expander("View deliberately injected defects"):
        st.dataframe(manifest, hide_index=True)

with model:
    st.subheader("Predict a return at checkout")
    regions, checks = readiness(cleaned)
    st.write("Target is the binary returned flag. Use region, category, quantity and unit price as candidate inputs available at checkout.")
    columns = st.columns(3)
    columns[0].metric("Positive labels", f"{checks['positive_labels']:,}")
    columns[1].metric("Return prevalence", f"{checks['positive_rate']:.1%}")
    columns[2].metric("Refund signal agreement", f"{checks['refund_signal_agreement']:.1%}")
    st.warning("Exclude refund amount because it becomes available after the outcome. Exclude the transaction ID from features and use order date for splitting.")
    st.subheader("Regional coverage")
    display = regions.assign(
        share=regions.share.map("{:.1%}".format),
        return_rate=regions.return_rate.map("{:.1%}".format),
    ).rename(columns={"share": "Record share", "return_rate": "Return rate",
                      "under_10_pct": "Under 10% share"})
    st.dataframe(display)
    st.caption("Small regional cohorts can yield unstable estimates. The rates show a deliberately simulated coverage and outcome imbalance. Fairness requires validation with representative data and relevant group-level error measures.")
    st.subheader("Chronological holdout")
    st.write(f"Hold out orders from {checks['cutoff_date']} onwards. "
             f"{checks['train_rows']:,} training rows, {checks['holdout_rows']:,} holdout rows "
             f"and {checks['shared_transaction_ids']} shared transaction IDs.")
    st.write("Fit preprocessing on training data only. Evaluate against a prevalence baseline using precision, recall and a precision–recall curve. Confirm that outcome labels have had time to mature before splitting real data.")

with release:
    st.subheader("Privacy screening")
    st.dataframe(pd.DataFrame({"Raw": privacy(raw), "Clean": privacy(cleaned)}))
    st.caption("The screening counts unexpected fields and cells matching common contact or identifier patterns. Format checks can miss identifiers or produce false matches.")
    st.write("The generator uses fictional transactions and stores no customer profiles. For real data, minimize fields, review combinations that could identify people, restrict access to raw and quarantined data, and remove credentials from shared files.")
    st.subheader("Download case files")
    files = {
        "Raw transactions": "retail_raw.csv",
        "Clean transactions": "retail_clean.csv",
        "Cleaning decisions": "cleaning_log.csv",
        "Quarantined transactions": "quarantine.csv",
        "Defect manifest": "defect_manifest.csv",
        "Audit report": "audit.json",
    }
    for label, name in files.items():
        mime = "text/csv" if name.endswith(".csv") else "application/json"
        st.download_button(label, (DATA / name).read_bytes(), name, mime=mime)
