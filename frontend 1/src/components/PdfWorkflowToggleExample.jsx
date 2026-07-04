import React, { useState } from "react";
import { updatePdf, translatePdf } from "../services/apiService";
import "../styles/textTranslator.css";

const WORKFLOW = {
  REPLACE: "replace",
  TRANSLATE: "translate",
};

export default function PdfWorkflowToggleExample() {
  const [workflow, setWorkflow] = useState(WORKFLOW.REPLACE);
  const [file, setFile] = useState(null);
  const [pageNumber, setPageNumber] = useState("");
  const [sectionName, setSectionName] = useState("");
  const [oldText, setOldText] = useState("");
  const [newText, setNewText] = useState("");
  const [userInstructions, setUserInstructions] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const isTranslateMode = workflow === WORKFLOW.TRANSLATE;

  const resetResult = () => {
    setResult(null);
    setError("");
  };

  const handleWorkflowChange = (nextWorkflow) => {
    setWorkflow(nextWorkflow);
    resetResult();
  };

  const handleSubmit = async () => {
    resetResult();

    if (!file) {
      setError("Please upload a PDF file.");
      return;
    }

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append("file", file);

      let response;

      if (isTranslateMode) {
        formData.append("source_language", "English");
        formData.append("target_language", "Spanish");
        response = await translatePdf(formData);
      } else {
        const payload = [
          {
            language: "english",
            page_number: Number(pageNumber),
            section_name: sectionName,
            old_text: oldText,
            new_text: newText,
            user_instructions: userInstructions,
          },
        ];
        formData.append("payload", JSON.stringify(payload));
        response = await updatePdf(formData);
      }

      setResult(response);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="translator-container">
      <div className="translator-card ai-shell">
        <div className="hero-panel">
          <div className="hero-left">
            <span className="agent-badge">AI PDF Workflow</span>
            <h1 className="translator-title">
              {isTranslateMode ? "PDF Language Translation" : "PDF Text Replacement"}
            </h1>
            <p className="translator-subtitle">
              {isTranslateMode
                ? "Translate the complete PDF from English to Spanish while preserving the original layout."
                : "Replace selected PDF text with validation and layout-risk analysis."}
            </p>
          </div>
        </div>

        <div className="workflow-toggle-card">
          <button
            type="button"
            className={`workflow-toggle-button ${workflow === WORKFLOW.REPLACE ? "active" : ""}`}
            onClick={() => handleWorkflowChange(WORKFLOW.REPLACE)}
          >
            Text Replacement
          </button>
          <button
            type="button"
            className={`workflow-toggle-button ${workflow === WORKFLOW.TRANSLATE ? "active" : ""}`}
            onClick={() => handleWorkflowChange(WORKFLOW.TRANSLATE)}
          >
            PDF Translation
          </button>
        </div>

        <div className="section-card">
          <div className="section-card-header">
            <div>
              <p className="section-step">Step 1</p>
              <h2 className="section-title">
                {isTranslateMode ? "Upload PDF for Translation" : "Upload PDF and Replacement Details"}
              </h2>
            </div>
          </div>

          <label className="field-label">PDF File</label>
          <input
            className="file-input"
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            disabled={loading}
          />

          {isTranslateMode ? (
            <div className="translation-language-grid">
              <div className="instruction-field">
                <label className="field-label">Source Language</label>
                <input className="text-input" value="English" disabled />
              </div>
              <div className="instruction-field">
                <label className="field-label">Translate To</label>
                <input className="text-input" value="Spanish" disabled />
              </div>
            </div>
          ) : (
            <div className="instruction-grid">
              <div className="instruction-field">
                <label className="field-label">Page Number</label>
                <input className="text-input" value={pageNumber} onChange={(e) => setPageNumber(e.target.value)} />
              </div>
              <div className="instruction-field">
                <label className="field-label">Section Name</label>
                <input className="text-input" value={sectionName} onChange={(e) => setSectionName(e.target.value)} />
              </div>
              <div className="instruction-field full-width">
                <label className="field-label">Old Text</label>
                <textarea className="translator-textarea" value={oldText} onChange={(e) => setOldText(e.target.value)} />
              </div>
              <div className="instruction-field full-width">
                <label className="field-label">New Text</label>
                <textarea className="translator-textarea" value={newText} onChange={(e) => setNewText(e.target.value)} />
              </div>
              <div className="instruction-field full-width">
                <label className="field-label">User Instructions</label>
                <textarea className="translator-textarea" value={userInstructions} onChange={(e) => setUserInstructions(e.target.value)} />
              </div>
            </div>
          )}

          {error && <p className="upload-error-message">{error}</p>}

          <div className="button-row">
            <button className="submit-button primary-submit-button" onClick={handleSubmit} disabled={loading}>
              {loading ? "Processing..." : isTranslateMode ? "Translate PDF" : "Update PDF"}
            </button>
          </div>
        </div>

        {result?.url && (
          <div className="section-card result-section">
            <div className="success-banner-card">
              <div>
                <strong>{isTranslateMode ? "Translation completed" : "PDF update completed"}</strong>
                <p>{result.message}</p>
              </div>
            </div>
            <a className="download-button" href={`http://localhost:8000${result.url}`} download={result.fileName}>
              Download {result.fileName || "PDF"}
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
