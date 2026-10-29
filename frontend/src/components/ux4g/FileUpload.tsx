import React, { useRef, useState } from "react";
import { Icon } from "./Icon";

export interface FileUploadProps {
  id?: string;
  accept?: string;
  maxSizeBytes?: number;
  onFileSelect?: (file: File) => void;
  selectedFile?: File | null;
  onFileClear?: () => void;
  label?: string;
  hint?: string;
  error?: string;
  disabled?: boolean;
}

/**
 * UX4G File Upload Component
 * Drag-and-drop file upload region with browse button and keyboard support.
 */
export const FileUpload: React.FC<FileUploadProps> = ({
  id = "file-upload",
  accept,
  maxSizeBytes,
  onFileSelect,
  selectedFile,
  onFileClear,
  label = "Upload file",
  hint,
  error,
  disabled = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [internalError, setInternalError] = useState<string | null>(null);

  const displayError = error || internalError;

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];

    if (maxSizeBytes && file.size > maxSizeBytes) {
      setInternalError(
        `File is too large (${(file.size / (1024 * 1024)).toFixed(1)}MB). Max allowed: ${(
          maxSizeBytes /
          (1024 * 1024)
        ).toFixed(1)}MB`
      );
      return;
    }

    setInternalError(null);
    onFileSelect?.(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;
    handleFiles(e.dataTransfer.files);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-full flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-sm font-semibold select-none">
          {label}
        </label>
      )}
      {hint && <p className="text-xs ux4g-text-neutral-tertiary mb-1">{hint}</p>}

      <input
        ref={fileInputRef}
        id={id}
        type="file"
        accept={accept}
        disabled={disabled}
        className="sr-only"
        onChange={(e) => handleFiles(e.target.files)}
      />

      {selectedFile ? (
        <div className="flex items-center justify-between p-3 border rounded-lg ux4g-bg-neutral-soft ux4g-border-neutral-subtle">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <Icon name="description" size="md" color="primary" aria-hidden="true" />
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{selectedFile.name}</p>
              <p className="text-xs ux4g-text-neutral-tertiary">{formatFileSize(selectedFile.size)}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              if (fileInputRef.current) fileInputRef.current.value = "";
              onFileClear?.();
            }}
            disabled={disabled}
            aria-label="Remove selected file"
            className="p-1 rounded hover:opacity-75 focus:outline-none focus:ring-2 focus:ring-offset-1 ux4g-text-neutral-secondary"
          >
            <Icon name="close" size="sm" color="inherit" aria-hidden="true" />
          </button>
        </div>
      ) : (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            if (!disabled) setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => !disabled && fileInputRef.current?.click()}
          onKeyDown={(e) => {
            if ((e.key === "Enter" || e.key === " ") && !disabled) {
              e.preventDefault();
              fileInputRef.current?.click();
            }
          }}
          tabIndex={disabled ? -1 : 0}
          role="button"
          aria-label={label}
          className={`border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
            isDragOver
              ? "ux4g-border-primary ux4g-bg-primary-soft"
              : displayError
              ? "ux4g-border-error ux4g-bg-neutral-soft"
              : "ux4g-border-neutral-subtle ux4g-bg-neutral-elevated"
          } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          <Icon name="cloud_upload" size="xl" color="primary" aria-hidden="true" />
          <p className="mt-2 text-sm font-medium">
            Drag and drop your file here, or{" "}
            <span className="ux4g-text-brand-primary underline font-semibold">browse</span>
          </p>
          {accept && <p className="text-xs ux4g-text-neutral-tertiary mt-1">Accepted: {accept}</p>}
        </div>
      )}

      {displayError && (
        <p role="alert" className="text-xs font-semibold ux4g-text-error mt-0.5">
          {displayError}
        </p>
      )}
    </div>
  );
};
