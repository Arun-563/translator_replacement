import React, { useEffect, useRef, useState } from "react";
import "../styles/textTranslator.css";
import { updatePdf, translatePdf } from "../services/apiService";

//remove the mock response when done testing
const MOCK_RESPONSE = {
    "success": true,
    "message": "PDF translated successfully",
    "translation_result": {
        "source_language": "English",
        "target_language": "Spanish",
        "storage_mode": "local",
        "pdf_name": "2026-07-01_12_47_19_EN_04_Sustainable_Cafe_Operations_Note.pdf",
        "json_name": "2026-07-01_12_47_19_EN_04_Sustainable_Cafe_Operations_Note.json",
        "translated_json_name": "translated_2026-07-01_12_47_19_EN_04_Sustainable_Cafe_Operations_Note.json",
        "pdf_local": "local://C:/Users/shahrin.fatima/Downloads/translator/kansas-document-localization-BE 1 (1)/kansas-document-localization-BE/backend_code/static/uploads/2026-07-01_12_47_19_EN_04_Sustainable_Cafe_Operations_Note.pdf",
        "json_local": "local://C:/Users/shahrin.fatima/Downloads/translator/kansas-document-localization-BE 1 (1)/kansas-document-localization-BE/backend_code/static/json/2026-07-01_12_47_19_EN_04_Sustainable_Cafe_Operations_Note.json",
        "translated_block_count": 20,
        "replaced_count": 20,
        "translation_validation": {
            "total_blocks_validated": 20,
            "passed_count": 13,
            "failed_count": 7,
            "average_score": 0.894,
            "failed_blocks": {
                "tmprrn8ij64.pdf_p1_b5": {
                    "is_valid": false,
                    "score": 0.75,
                    "severity": "MEDIUM",
                    "issues": [
                        "Translation is not semantically correct"
                    ],
                    "suggested_fix": "NT Prueba de Traducción para Northstar Viaje Documento"
                },
                "tmprrn8ij64.pdf_p1_b6": {
                    "is_valid": false,
                    "score": 0.75,
                    "severity": "MEDIUM",
                    "issues": [
                        "Translation is not semantically correct"
                    ],
                    "suggested_fix": "© 2026 — Northstar Travel — Página 1 con solo parágrafos"
                },
                "tmprrn8ij64.pdf_p1_b11": {
                    "is_valid": false,
                    "score": 0.75,
                    "severity": "MEDIUM",
                    "issues": [
                        "Translation misses important meaning: 'paquete desechable' should be 'embalaje desechable', and the phrase 'pruebas de traducción al cliente' is unclear, it should be 'pruebas de traducción para uso con clientes'."
                    ],
                    "suggested_fix": "El café introduce una rutina de sostenibilidad que reduce el embalaje desechable, destaca los ingredientes estacionales y mejora la comunicación con proveedores. El documento utiliza un tono empresarial alegre adecuado para pruebas de traducción para uso con clientes."
                },
                "tmprrn8ij64.pdf_p2_b5": {
                    "is_valid": false,
                    "score": 0.75,
                    "severity": "MEDIUM",
                    "issues": [
                        "Translation misses the original purpose of being a test document name"
                    ],
                    "suggested_fix": "Documento de Prueba de Traducción NT Northstar Travel"
                },
                "tmprrn8ij64.pdf_p2_b8": {
                    "is_valid": false,
                    "score": 0.75,
                    "severity": "MEDIUM",
                    "issues": [
                        "Translation adds 'sostenibilidad local' which is not in the original text"
                    ],
                    "suggested_fix": "Las descripciones del menú explican los descuentos en tazas reutilizables y la fuente local de manera clara. El mensaje evita las afirmaciones técnicas y se centra en opciones prácticas que los huéspedes pueden entender rápidamente."
                },
                "tmprrn8ij64.pdf_p2_b11": {
                    "is_valid": false,
                    "score": 0.75,
                    "severity": "MEDIUM",
                    "issues": [
                        "Translation contains an untranslated term 'branded' and incorrectly uses 'entre diferentes idiomas' instead of a proper comparison context"
                    ],
                    "suggested_fix": "Al final de cada mes, el equipo revisa los totales de desperdicio, los items populares en la carta y las sugerencias del cliente. El resumen escrito ayuda a comparar cómo los números, los sustantivos y los encabezados se comportan en diferentes contextos."
                },
                "tmprrn8ij64.pdf_p2_b12": {
                    "is_valid": false,
                    "score": 0.85,
                    "severity": "MEDIUM",
                    "issues": [
                        "'espaciado visual' should be 'espacio visual'",
                        "missing the concept of translation pipeline"
                    ],
                    "suggested_fix": "Texto adicional de revisión para esta sección describe el comportamiento del documento, el espacio visual y la continuidad del contenido. El objetivo es verificar que una línea de procesamiento de traducción puede manejar prosa realista sin depender de tablas, placeholders repetidos o líneas de muestra idénticas."
                }
            },
            "validation_error": null
        },
        "replacement_logs": [],
        "output_file_name": "translated_2026-07-01_12_47_19_EN_04_Sustainable_Cafe_Operations_Note.pdf",
        "output_path": "C:\\Users\\shahrin.fatima\\Downloads\\translator\\kansas-document-localization-BE 1 (1)\\kansas-document-localization-BE\\backend_code\\static\\downloads\\translated_2026-07-01_12_47_19_EN_04_Sustainable_Cafe_Operations_Note.pdf",
        "output_url": "/static/downloads/translated_2026-07-01_12_47_19_EN_04_Sustainable_Cafe_Operations_Note.pdf"
    }
}

const WORKFLOW = {
  REPLACE: "replace",
  TRANSLATE: "translate",
};

const USE_MOCK_RESPONSE = false;

const replacementAgentMessages = [
  "Processing request...",
  "Analyzing document...",
  "Generating updated PDF...",
];

const translationAgentMessages = [
  "Uploading PDF...",
  "Extracting layout JSON...",
  "Translating English text to Spanish...",
  "Generating translated PDF...",
];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const TextTranslator = () => {
  const [workflow, setWorkflow] = useState(WORKFLOW.REPLACE);
  const [selectedFile, setSelectedFile] = useState(null);
  const [userInstructions, setUserInstructions] = useState("");

  const [instruction, setInstruction] = useState({
    language: "english",
    page_number: "",
    section_name: "",
    old_text: "",
    new_text: "",
  });

  const [outputFileUrl, setOutputFileUrl] = useState("");
  const [fileName, setFileName] = useState("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isDownloaded, setIsDownloaded] = useState(false);

  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadErrorMessage, setUploadErrorMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [summary, setSummary] = useState(null);
  const [layoutWarnings, setLayoutWarnings] = useState([]);
  const [currentStep, setCurrentStep] = useState(0);

  const [translationValidation, setTranslationValidation] = useState(null);
  const [translationValidationDetails, setTranslationValidationDetails] = useState([]);

  const [fieldErrors, setFieldErrors] = useState({
    file: "",
    page_number: "",
    section_name: "",
    old_text: "",
    new_text: "",
    same_text: "",
    user_instructions: "",
  });

  const fileInputRef = useRef(null);

  const isTranslateMode = workflow === WORKFLOW.TRANSLATE;

  const agentMessages = isTranslateMode
    ? translationAgentMessages
    : replacementAgentMessages;

  const processSteps = isTranslateMode
    ? [
        {
          title: "Upload PDF",
          description: selectedFile ? "PDF received and validated." : "Waiting for file upload.",
          icon: "📄",
          complete: !!selectedFile,
          running: false,
        },
        {
          title: "Extract Layout JSON",
          description: "Reading PDF text blocks and layout metadata.",
          icon: "🌐",
          complete: progress > 35 || !!outputFileUrl,
          running: loading && progress <= 35,
        },
        {
          title: "Translation & Validation",
          description: "Translating English text to Spanish.",
          icon: "🧠",
          complete: !!outputFileUrl,
          running: loading && progress > 35 && !outputFileUrl,
        },
        {
          title: "PDF Reconstruction",
          description: "Generating translated PDF with preserved layout.",
          icon: "⚙️",
          complete: !!outputFileUrl,
          running: false,
        },
      ]
    : [
        {
          title: "Upload PDF",
          description: selectedFile ? "PDF received and validated." : "Waiting for file upload.",
          icon: "📄",
          complete: !!selectedFile,
          running: false,
        },
        {
          title: "AI Content Matching",
          description: "Mapping requested edits to document content.",
          icon: "🧠",
          complete: progress > 35 || !!outputFileUrl,
          running: loading && progress <= 35,
        },
        {
          title: "Layout Analysis",
          description: "Checking spacing and fit before replacement.",
          icon: "📐",
          complete: progress > 65 || !!outputFileUrl,
          running: loading && progress > 35 && progress <= 65,
        },
        {
          title: "PDF Update",
          description: "Applying approved modifications.",
          icon: "⚙️",
          complete: !!outputFileUrl,
          running: loading && progress > 65 && !outputFileUrl,
        },
      ];

  useEffect(() => {
    let progressInterval;

    if (loading) {
      progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) return prev;
          return prev + 5;
        });
      }, 500);
    }

    return () => {
      if (progressInterval) clearInterval(progressInterval);
    };
  }, [loading]);

  useEffect(() => {
    if (!loading) return;
    if (currentStep >= agentMessages.length - 1) return;

    const messageTimer = setTimeout(() => {
      setCurrentStep((prev) => prev + 1);
    }, 2200);

    return () => clearTimeout(messageTimer);
  }, [loading, currentStep, agentMessages.length]);

  const resetResultState = () => {
    setErrorMessage("");
    setSuccessMessage("");
    setOutputFileUrl("");
    setFileName("");
    setIsDownloaded(false);
    setSummary(null);
    setLayoutWarnings([]);
    setTranslationValidation(null);
    setTranslationValidationDetails([]);
  };

  const countWords = (value) => {
    return value.trim() ? value.trim().split(/\s+/).length : 0;
  };

  const isInstructionComplete = () => {
    if (isTranslateMode) return !!selectedFile;

    return (
      instruction.language &&
      String(instruction.page_number).trim() !== "" &&
      instruction.section_name.trim() &&
      instruction.old_text.trim() &&
      instruction.new_text.trim() &&
      instruction.old_text.trim() !== instruction.new_text.trim()
    );
  };

  const normalizeFailedBlocks = (failedBlocks) => {
    if (!failedBlocks) return [];

    if (Array.isArray(failedBlocks)) {
      return failedBlocks.map((item, index) => ({
        block_id: item.block_id || `failed_block_${index + 1}`,
        ...item,
      }));
    }

    if (typeof failedBlocks === "object") {
      return Object.entries(failedBlocks).map(([blockId, blockData]) => ({
        block_id: blockId,
        ...blockData,
      }));
    }

    return [];
  };

  const formatValidationScore = (score) => {
    if (score === null || score === undefined || score === "") return "N/A";

    const numericScore = Number(score);

    if (Number.isNaN(numericScore)) return String(score);

    if (numericScore <= 1) {
      return `${(numericScore * 100).toFixed(1)}%`;
    }

    return numericScore.toFixed(2);
  };

  const getValidationScoreClass = (score) => {
    const numericScore = Number(score);

    if (Number.isNaN(numericScore)) return "score-neutral";

    if (numericScore >= 0.8) return "score-good";
    if (numericScore >= 0.6) return "score-warning";

    return "score-danger";
  };

  const formatIssues = (issues) => {
    if (!issues) return [];

    if (Array.isArray(issues)) return issues;

    return [String(issues)];
  };

  const validateFields = (
    currentInstruction = instruction,
    currentFile = selectedFile,
    currentUserInstructions = userInstructions
  ) => {
    const errors = {
      file: "",
      page_number: "",
      section_name: "",
      old_text: "",
      new_text: "",
      same_text: "",
      user_instructions: "",
    };

    if (!currentFile) {
      errors.file = "Please upload a PDF file.";
    }

    if (!isTranslateMode) {
      if (!String(currentInstruction.page_number).trim()) {
        errors.page_number = "Page number is required.";
      }

      if (!currentInstruction.section_name.trim()) {
        errors.section_name = "Section name is required.";
      }

      if (!currentInstruction.old_text.trim()) {
        errors.old_text = "Old text is required.";
      }

      if (!currentInstruction.new_text.trim()) {
        errors.new_text = "New text is required.";
      }

      if (
        currentInstruction.old_text.trim() &&
        currentInstruction.new_text.trim() &&
        currentInstruction.old_text.trim() === currentInstruction.new_text.trim()
      ) {
        errors.same_text = "Old text and new text cannot be the same.";
      }

      if (countWords(currentUserInstructions) > 200) {
        errors.user_instructions = "User instructions cannot exceed 200 words.";
      }
    }

    setFieldErrors(errors);
    return !Object.values(errors).some(Boolean);
  };

  const isSubmitDisabled =
    loading ||
    !selectedFile ||
    (!isTranslateMode &&
      (countWords(userInstructions) > 200 || !isInstructionComplete()));

  const handleWorkflowChange = (nextWorkflow) => {
    if (loading) return;

    setWorkflow(nextWorkflow);
    resetResultState();
    setProgress(0);
    setCurrentStep(0);

    setFieldErrors({
      file: selectedFile ? "" : "Please upload a PDF file.",
      page_number: "",
      section_name: "",
      old_text: "",
      new_text: "",
      same_text: "",
      user_instructions: "",
    });
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];

    setUploadMessage("");
    setUploadErrorMessage("");
    resetResultState();

    if (file) {
      const extension = file.name.split(".").pop()?.toLowerCase();
      const isPdf = file.type === "application/pdf" || extension === "pdf";

      if (!isPdf) {
        setSelectedFile(null);
        setUploadErrorMessage("Only PDF files are supported.");
        setFieldErrors((prev) => ({
          ...prev,
          file: "Please upload a PDF file.",
        }));
        event.target.value = "";
        return;
      }

      setSelectedFile(file);
      setUploadMessage(`${file.name} uploaded successfully.`);
      setUploadErrorMessage("");
      validateFields(instruction, file, userInstructions);
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setUploadMessage("");
    setUploadErrorMessage("");
    resetResultState();

    setFieldErrors((prev) => ({
      ...prev,
      file: "Please upload a PDF file.",
    }));

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleInstructionChange = (field, value) => {
    resetResultState();

    const updatedInstruction = {
      ...instruction,
      [field]: value,
    };

    setInstruction(updatedInstruction);
    validateFields(updatedInstruction, selectedFile, userInstructions);
  };

  const handleUserInstructionsChange = (event) => {
    resetResultState();

    const inputValue = event.target.value;
    const words = inputValue.trim() ? inputValue.trim().split(/\s+/) : [];
    let finalValue = inputValue;

    if (words.length > 200) {
      finalValue = words.slice(0, 200).join(" ");
    }

    setUserInstructions(finalValue);
    validateFields(instruction, selectedFile, finalValue);
  };

  const handleSubmit = async () => {
    resetResultState();

    const isValid = validateFields();

    if (!isValid) {
      setErrorMessage("Please correct the highlighted fields.");
      return;
    }

    setLoading(true);
    setProgress(0);
    setCurrentStep(0);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      if (isTranslateMode) {
        formData.append("source_language", "English");
        formData.append("target_language", "Spanish");

        const translationResponse = USE_MOCK_RESPONSE
          ? await sleep(2500).then(() => MOCK_RESPONSE)
          : await translatePdf(formData);

        console.log("Parsed translation API response:", translationResponse);

        if (!translationResponse.success) {
          setErrorMessage(translationResponse.message || "PDF translation failed.");
          return;
        }

        const translationResult =
          translationResponse.translation_result ||
          translationResponse.translationResult ||
          {};

        const validationResult = translationResult.translation_validation || {};
        const failedBlocks = normalizeFailedBlocks(validationResult.failed_blocks);

        setProgress(100);
        setCurrentStep(agentMessages.length - 1);

        setOutputFileUrl(
          translationResult.output_url ||
          translationResult.url ||
          translationResponse.url ||
          ""
        );

        setFileName(
          translationResult.output_file_name ||
          translationResponse.fileName ||
          ""
        );

        setSuccessMessage("Document translated successfully");

        setSummary({
          processed_file: translationResult.pdf_name || selectedFile.name,
          source_language: translationResult.source_language || "English",
          target_language: translationResult.target_language || "Spanish",
          translated_blocks: translationResult.translated_block_count ?? 0,
          applied_updates: translationResult.replaced_count ?? 0,
          skipped_updates: 0,
        });

        setTranslationValidation({
          total_blocks_validated: validationResult.total_blocks_validated ?? 0,
          passed_count: validationResult.passed_count ?? 0,
          failed_count: validationResult.failed_count ?? 0,
          average_score: validationResult.average_score ?? null,
          validation_error: validationResult.validation_error || "",
        });

        setTranslationValidationDetails(failedBlocks);
        setLayoutWarnings([]);
        return;
      }

      formData.append(
        "payload",
        JSON.stringify([
          {
            language: instruction.language,
            page_number: Number(instruction.page_number),
            section_name: instruction.section_name.trim(),
            old_text: instruction.old_text.trim(),
            new_text: instruction.new_text.trim(),
            file: selectedFile.name,
            user_instructions: userInstructions.trim(),
          },
        ])
      );

      const replacementResponse = await updatePdf(formData);
      console.log("Parsed replacement API response:", replacementResponse);

      if (!replacementResponse.success) {
        setErrorMessage(replacementResponse.message || "PDF update failed.");
        return;
      }

      const replacementResult = replacementResponse.replacementResult;

      if (replacementResult && Number(replacementResult.replaced_count) > 0) {
        setProgress(100);
        setCurrentStep(agentMessages.length - 1);
        setOutputFileUrl(replacementResponse.url);
        setFileName(replacementResponse.fileName);
        setSuccessMessage("Document updated successfully");

        setSummary({
          processed_file: selectedFile.name,
          total_updates: replacementResult.replaced_count,
          applied_updates: replacementResult.replaced_count,
          skipped_updates: 0,
        });

        const derivedWarnings = Array.isArray(replacementResult.logs)
          ? replacementResult.logs
              .filter((item) => String(item.status).toUpperCase() !== "REPLACED")
              .map((item) => {
                const pageText = item.page ? `Page ${item.page}: ` : "";
                return `${pageText}${item.status}`;
              })
          : [];

        setLayoutWarnings(derivedWarnings);
      } else if (replacementResult && Number(replacementResult.replaced_count) === 0) {
        setProgress(100);
        setCurrentStep(agentMessages.length - 1);
        setOutputFileUrl("");
        setFileName("");
        setSuccessMessage("Document processed but no text was updated");

        setSummary({
          processed_file: selectedFile.name,
          total_updates: 0,
          applied_updates: 0,
          skipped_updates: 0,
        });

        const derivedWarnings = Array.isArray(replacementResult.logs)
          ? replacementResult.logs.map((item) => {
              const pageText = item.page ? `Page ${item.page}: ` : "";
              return `${pageText}${item.status}`;
            })
          : [];

        setLayoutWarnings(derivedWarnings);
      } else {
        setErrorMessage(replacementResponse.message || "PDF processing failed.");
      }
    } catch (error) {
      console.error("Submit error:", error);
      setOutputFileUrl("");
      setFileName("");
      setSuccessMessage("");
      setSummary(null);
      setLayoutWarnings([]);
      setTranslationValidation(null);
      setTranslationValidationDetails([]);
      setErrorMessage(error.message || "Something went wrong while processing the PDF.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!outputFileUrl) return;

    try {
      const downloadUrl = outputFileUrl.startsWith("http")
        ? outputFileUrl
        : `http://localhost:8000${outputFileUrl}`;

      const response = await fetch(downloadUrl);

      if (!response.ok) {
        throw new Error("Failed to download file.");
      }

      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = fileName || "";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      window.URL.revokeObjectURL(blobUrl);
      setIsDownloaded(true);
    } catch (error) {
      console.error("Download error:", error);
      setErrorMessage("Failed to download the PDF.");
    }
  };

  const renderResultPanel = () => {
    return (
      <div className="side-card result-section full-width-result-section">
        <div className="section-card-header">
          <div>
            <p className="section-step">{isTranslateMode ? "Step 3" : "Step 4"}</p>
            <h3 className="section-title">Output &amp; Review</h3>
          </div>
        </div>

        {errorMessage && !outputFileUrl ? (
          <div className="result-error-box modern-error-box">
            <div className="result-box-icon">⚠️</div>
            <div>
              <strong>Processing Error</strong>
              <p>{errorMessage}</p>
            </div>
          </div>
        ) : !outputFileUrl ? (
          <div className="result-placeholder modern-placeholder">
            <div className="result-box-icon">✨</div>
            <p>Download option and validation details will appear here after processing.</p>
          </div>
        ) : (
          <>
            {successMessage && (
              <div className="success-banner-card">
                <div className="result-box-icon">✅</div>
                <div>
                  <strong>{successMessage}</strong>
                  <p>
                    {isTranslateMode
                      ? "Your translated PDF is ready for review."
                      : "Your updated PDF is ready for review."}
                  </p>
                </div>
              </div>
            )}

            <div className="result-grid">
              {summary && (
                <div className="summary-card">
                  <h4 className="summary-title">
                    {isTranslateMode ? "Translation Summary" : "Update Summary"}
                  </h4>

                  <ul className="summary-list">
                    {summary.processed_file && (
                      <li>
                        <strong>Processed File:</strong> {summary.processed_file}
                      </li>
                    )}
                    {summary.source_language && (
                      <li>
                        <strong>Source Language:</strong> {summary.source_language}
                      </li>
                    )}
                    {summary.target_language && (
                      <li>
                        <strong>Target Language:</strong> {summary.target_language}
                      </li>
                    )}
                    

                    {isTranslateMode && translationValidation && (
                      <>
                        <li>
                          <strong>Validation Score:</strong>{" "}
                          <span
                            className={`validation-score-inline ${getValidationScoreClass(
                              translationValidation.average_score
                            )}`}
                          >
                            {formatValidationScore(translationValidation.average_score)}
                          </span>
                        </li>
                      </>
                    )}
                  </ul>

                  <div className="download-row result-download-row">
                    <button className="download-button" onClick={handleDownload}>
                      {isDownloaded
                        ? "Downloaded"
                        : isTranslateMode
                        ? "Download Translated PDF"
                        : "Download Updated PDF"}
                    </button>
                  </div>

                  {isDownloaded && (
                    <p className="download-success-message">
                      {isTranslateMode
                        ? "Translated PDF downloaded successfully"
                        : "Updated PDF downloaded successfully"}
                    </p>
                  )}
                </div>
              )}

              <div className="summary-card warning-card">
                <h4 className="summary-title">Layout Warnings</h4>
                {layoutWarnings.length > 0 ? (
                  <ul className="summary-list">
                    {layoutWarnings.map((warning, index) => (
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="no-warning-text">No layout warnings reported.</p>
                )}
              </div>
            </div>

            {isTranslateMode && translationValidation && (
              <div className="summary-card validation-card validation-card-wide">
                <div className="validation-header-row">
                  <div>
                    <h4 className="summary-title">Translation Validation</h4>
                    <p className="validation-subtitle">
                      Semantic validation quality check for translated PDF blocks.
                    </p>
                  </div>

                  <div
                    className={`validation-score-pill ${getValidationScoreClass(
                      translationValidation.average_score
                    )}`}
                  >
                    {formatValidationScore(translationValidation.average_score)}
                  </div>
                </div>

                <div className="validation-metrics-grid">
                  <div className="validation-metric-box">
                    <span>Total</span>
                    <strong>{translationValidation.total_blocks_validated}</strong>
                  </div>

                  <div className="validation-metric-box success-metric">
                    <span>Passed</span>
                    <strong>{translationValidation.passed_count}</strong>
                  </div>

                  <div className="validation-metric-box danger-metric">
                    <span>Failed</span>
                    <strong>{translationValidation.failed_count}</strong>
                  </div>
                </div>

                {translationValidation.validation_error && (
                  <div className="validation-error-note">
                    <strong>Validation Error:</strong>{" "}
                    {translationValidation.validation_error}
                  </div>
                )}

                <div className="validation-detail-box validation-detail-grid">
                  {translationValidationDetails.length > 0 ? (
                    translationValidationDetails.map((block, index) => (
                      <div className="validation-detail-item" key={block.block_id || index}>
                        <div className="validation-detail-title">
                          <span>Failed Block {index + 1}</span>
                          <code>{block.block_id}</code>
                        </div>

                        <div className="validation-detail-meta-row">
                          <span
                            className={`validation-severity-badge severity-${String(
                              block.severity || "unknown"
                            ).toLowerCase()}`}
                          >
                            {block.severity || "UNKNOWN"}
                          </span>

                          <span
                            className={`validation-block-score ${getValidationScoreClass(
                              block.score
                            )}`}
                          >
                            Score: {formatValidationScore(block.score)}
                          </span>
                        </div>

                        {formatIssues(block.issues).length > 0 && (
                          <div className="validation-issues-list">
                            <strong>Issues:</strong>
                            <ul>
                              {formatIssues(block.issues).map((issue, issueIndex) => (
                                <li key={issueIndex}>{issue}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {block.suggested_fix && (
                          <div className="suggested-fix-box">
                            <strong>Suggested Fix:</strong>
                            <p>{block.suggested_fix}</p>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="no-warning-text">No failed validation blocks reported.</p>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  };

  return (
    <div className="translator-container">
      <div className="translator-card ai-shell">
        <div className="hero-panel">
          <div className="hero-left">
            <div className="agent-badge">AI assisted</div>
            <h2 className="translator-title">
              {isTranslateMode ? "PDF Language Translation" : "PDF Update Workflow"}
            </h2>
            <p className="translator-subtitle">
              {isTranslateMode
                ? "Upload a PDF and translate the full document from English to Spanish while preserving the layout."
                : "Upload a PDF, provide update instructions, submit and download the updated output."}
            </p>
          </div>

          <div className="hero-right">
            <div className="hero-stat-card">
              <span className="hero-stat-label">Mode</span>
              <strong>{isTranslateMode ? "Translation" : "Replacement"}</strong>
            </div>
            <div className="hero-stat-card">
              <span className="hero-stat-label">Output</span>
              <strong>{outputFileUrl ? "Ready" : loading ? "Processing" : "Pending"}</strong>
            </div>
          </div>
        </div>

        <div className="workflow-toggle-card">
          <button
            type="button"
            className={`workflow-toggle-button ${
              workflow === WORKFLOW.REPLACE ? "active" : ""
            }`}
            onClick={() => handleWorkflowChange(WORKFLOW.REPLACE)}
            disabled={loading}
          >
            Text Replacement
          </button>

          <button
            type="button"
            className={`workflow-toggle-button ${
              workflow === WORKFLOW.TRANSLATE ? "active" : ""
            }`}
            onClick={() => handleWorkflowChange(WORKFLOW.TRANSLATE)}
            disabled={loading}
          >
            PDF Translation
          </button>
        </div>

        <div className="app-layout improved-app-layout">
          <div className="main-column">
            <div className="section-card">
              <div className="section-card-header">
                <div>
                  <p className="section-step">Step 1</p>
                  <h3 className="section-title">Upload PDF</h3>
                </div>
              </div>

              <div className="upload-box upload-box-modern">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  className="file-input"
                  disabled={loading}
                />

                <p className="upload-note">Supported: PDF files only</p>

                {selectedFile && (
                  <div className="file-name-box">
                    <div className="file-name-header">
                      <span className="file-name-label">Selected File:</span>
                      <button
                        type="button"
                        className="clear-file-button"
                        onClick={handleClearFile}
                        aria-label="Clear uploaded file"
                        disabled={loading}
                      >
                        ×
                      </button>
                    </div>
                    <span className="file-name">{selectedFile.name}</span>
                  </div>
                )}

                {uploadMessage && (
                  <p className="upload-success-message">{uploadMessage}</p>
                )}
                {uploadErrorMessage && (
                  <p className="upload-error-message">{uploadErrorMessage}</p>
                )}
                {fieldErrors.file && (
                  <p className="field-error-message upload-field-error">
                    {fieldErrors.file}
                  </p>
                )}
              </div>
            </div>

            {isTranslateMode ? (
              <div className="section-card">
                <div className="section-card-header">
                  <div>
                    <p className="section-step">Step 2</p>
                    <h3 className="section-title">Translation Settings</h3>
                  </div>
                </div>

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

                <div className="button-row">
                  <button
                    className="submit-button primary-submit-button"
                    onClick={handleSubmit}
                    disabled={isSubmitDisabled}
                  >
                    {loading ? "Translating..." : "Translate PDF"}
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="section-card">
                  <div className="section-card-header">
                    <div>
                      <p className="section-step">Step 2</p>
                      <h3 className="section-title">User Instructions</h3>
                    </div>
                  </div>

                  <div className="textarea-with-meta">
                    <textarea
                      className="translator-textarea"
                      placeholder="Enter additional instructions for how updates should be applied..."
                      value={userInstructions}
                      onChange={handleUserInstructionsChange}
                      rows={4}
                      disabled={loading}
                    />

                    <div className="instruction-meta-row">
                      <p className="word-count-note">
                        Word count:{" "}
                        <span
                          className={
                            countWords(userInstructions) >= 200
                              ? "word-count-limit"
                              : ""
                          }
                        >
                          {countWords(userInstructions)} / 200
                        </span>
                      </p>

                      {fieldErrors.user_instructions && (
                        <p className="field-error-message side-error">
                          {fieldErrors.user_instructions}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="section-card">
                  <div className="section-header-row">
                    <div>
                      <p className="section-step">Step 3</p>
                      <h3 className="instruction-heading">Update Instructions</h3>
                    </div>
                  </div>

                  <div className="instruction-list">
                    <div className="instruction-card modern-instruction-card">
                      <div className="instruction-grid">
                        <div className="instruction-field">
                          <label className="field-label">Language</label>
                          <div className="field-input-with-error">
                            <select
                              className="language-dropdown"
                              value={instruction.language}
                              onChange={(e) =>
                                handleInstructionChange("language", e.target.value)
                              }
                              disabled={loading}
                            >
                              <option value="english">English</option>
                              <option value="spanish">Spanish</option>
                            </select>
                          </div>
                        </div>

                        <div className="instruction-field">
                          <label className="field-label">Page Number</label>
                          <div className="field-input-with-error">
                            <input
                              type="number"
                              min="1"
                              className="text-input"
                              value={instruction.page_number}
                              onChange={(e) =>
                                handleInstructionChange("page_number", e.target.value)
                              }
                              placeholder="Enter page number"
                              disabled={loading}
                            />
                          </div>
                          <p className="field-error-message">
                            {fieldErrors.page_number || ""}
                          </p>
                        </div>

                        <div className="instruction-field full-width">
                          <label className="field-label">Section Name</label>
                          <div className="field-input-with-error">
                            <input
                              type="text"
                              className="text-input"
                              value={instruction.section_name}
                              onChange={(e) =>
                                handleInstructionChange("section_name", e.target.value)
                              }
                              placeholder="Enter section name"
                              disabled={loading}
                            />
                          </div>
                          <p className="field-error-message">
                            {fieldErrors.section_name || ""}
                          </p>
                        </div>

                        <div className="instruction-field full-width">
                          <label className="field-label">Old Text</label>
                          <div className="field-input-with-error field-input-with-error-textarea">
                            <textarea
                              className="translator-textarea small-textarea"
                              value={instruction.old_text}
                              onChange={(e) =>
                                handleInstructionChange("old_text", e.target.value)
                              }
                              placeholder="Enter old text"
                              rows={4}
                              disabled={loading}
                            />
                          </div>
                          <p className="field-error-message">
                            {fieldErrors.old_text || ""}
                          </p>
                        </div>

                        <div className="instruction-field full-width">
                          <label className="field-label">New Text</label>
                          <div className="field-input-with-error field-input-with-error-textarea">
                            <textarea
                              className="translator-textarea small-textarea"
                              value={instruction.new_text}
                              onChange={(e) =>
                                handleInstructionChange("new_text", e.target.value)
                              }
                              placeholder="Enter new text"
                              rows={4}
                              disabled={loading}
                            />
                          </div>
                          <p className="field-error-message">
                            {fieldErrors.new_text || fieldErrors.same_text || ""}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="button-row">
                    <button
                      className="submit-button primary-submit-button"
                      onClick={handleSubmit}
                      disabled={isSubmitDisabled}
                    >
                      {loading ? "Submitted" : "Submit"}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="side-column run-monitor-column">
            <div className="side-card run-monitor-card">
              <div className="section-card-header">
                <div>
                  <p className="section-step">Live Status</p>
                  <h3 className="section-title">Run Monitor</h3>
                </div>
              </div>

              <div className="monitor-status-card">
                {loading ? (
                  <>
                    <div className="processing-loader-row">
                      <div className="processing-spinner" />
                      <div>
                        <strong>Processing in progress</strong>
                        <p>
                          {progress >= 90
                            ? "Final PDF generation can take a little longer. The app is still working."
                            : agentMessages[currentStep]}
                        </p>
                      </div>
                    </div>

                    <div className="progress-wrapper progress-wrapper-modern compact-progress">
                      <div className="progress-header">
                        <span>{agentMessages[currentStep]}</span>
                        <span>{progress}%</span>
                      </div>
                      <div className="progress-bar-track">
                        <div
                          className="progress-bar-fill"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="progress-idle-card compact-idle-card">
                    <div className="idle-chip">
                      {outputFileUrl ? "Completed" : "Awaiting Run"}
                    </div>
                    <p className="idle-text">
                      {outputFileUrl
                        ? "Output is ready below."
                        : isTranslateMode
                        ? "Upload a PDF and submit to begin translation."
                        : "Submit the updates to begin processing."}
                    </p>
                  </div>
                )}
              </div>

              <div className="agent-activity-stack compact-agent-stack">
                {processSteps.map((step, index) => (
                  <div
                    key={step.title}
                    className={`activity-item compact-activity-item ${
                      step.complete ? "activity-complete" : ""
                    } ${step.running ? "activity-running" : ""}`}
                  >
                    <span
                      className={`activity-dot ${
                        step.running
                          ? "active-dot pulse-dot"
                          : step.complete
                          ? "active-dot"
                          : ""
                      }`}
                    />

                    <div className="activity-content">
                      <div className="activity-title-row">
                        <strong>
                          {index + 1}. {step.title}
                        </strong>
                        <span className="activity-icon">{step.icon}</span>
                      </div>
                      <p>{step.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {renderResultPanel()}
      </div>
    </div>
  );
};

export default TextTranslator;