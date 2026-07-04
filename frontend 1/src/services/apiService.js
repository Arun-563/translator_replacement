const API_BASE_URL = "http://localhost:8000";

export const updatePdf = async (formData) => {
  const response = await fetch(`${API_BASE_URL}/upload-pdf`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json();
  console.log("PDF replacement API raw response:", data);

  if (!response.ok) {
    throw new Error(
      data?.error ||
        data?.detail ||
        data?.message ||
        "PDF replacement request failed"
    );
  }

  const replacementResult = data?.replacement_result || null;

  return {
    success: data.success,
    message: data.message || "",
    replacementResult,
    url: replacementResult?.output_url || "",
    fileName: replacementResult?.output_file_name || "",
  };
};

export const translatePdf = async (formData) => {
  const response = await fetch(`${API_BASE_URL}/translate-pdf`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json();
  console.log("PDF translation API raw response:", data);

  if (!response.ok) {
    throw new Error(
      data?.error ||
        data?.detail ||
        data?.message ||
        "PDF translation request failed"
    );
  }

  const translationResult = data?.translation_result || null;
  const validationResult = translationResult?.translation_validation || {};
  return {
    success: data.success,
    message: data.message || "",
    translationResult,
    url: translationResult?.output_url || "",
    fileName: translationResult?.output_file_name || "",
    translatedBlockCount: translationResult?.translated_block_count || 0,
    replacedCount: translationResult?.replaced_count || 0,
    translationValidation: validationResult,
  };
};
