import React, { useRef } from "react";

export interface OtpInputProps {
  id?: string;
  length?: number;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  isError?: boolean;
  state?: "default" | "error" | "success" | "warning";
  ariaLabelPrefix?: string;
  "aria-describedby"?: string;
  className?: string;
}

/**
 * UX4G OTP Input Component
 * 6-box accessible OTP input with auto-advance, paste, and backspace handling.
 */
export const OtpInput: React.FC<OtpInputProps> = ({
  id,
  length = 6,
  value = "",
  onChange,
  disabled = false,
  isError = false,
  state = "default",
  ariaLabelPrefix = "Digit",
  "aria-describedby": ariaDescribedBy,
  className = "",
}) => {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Array of single digit chars padded to length
  const digits = Array.from({ length }, (_, i) => value[i] || "");
  const effectiveError = isError || state === "error";

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>, index: number) => {
    const raw = e.target.value;
    if (raw.length > 1) {
      const cleanDigits = raw.replace(/\D/g, "").slice(0, length);
      if (cleanDigits.length > 0) {
        onChange(cleanDigits);
        const focusIndex = Math.min(cleanDigits.length, length - 1);
        inputRefs.current[focusIndex]?.focus();
      }
      return;
    }
    const char = raw.slice(-1);
    if (char && !/^\d$/.test(char)) return; // Allow numbers only

    const newDigits = [...digits];
    newDigits[index] = char;
    const nextVal = newDigits.join("");
    onChange(nextVal);

    if (char && index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === "Backspace") {
      if (!digits[index] && index > 0) {
        inputRefs.current[index - 1]?.focus();
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      e.preventDefault();
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < length - 1) {
      e.preventDefault();
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").trim();
    if (!pasted) return;

    // Filter only digits and slice to length
    const cleanDigits = pasted.replace(/\D/g, "").slice(0, length);
    if (cleanDigits.length > 0) {
      onChange(cleanDigits);
      const focusIndex = Math.min(cleanDigits.length, length - 1);
      inputRefs.current[focusIndex]?.focus();
    }
  };

  return (
    <div
      role="group"
      aria-label="One-time password input"
      className={`flex items-center gap-2 ${className}`.trim()}
    >
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(el) => {
            inputRefs.current[index] = el;
          }}
          id={index === 0 && id ? id : undefined}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={index === 0 ? length : 1}
          value={digit}
          disabled={disabled}
          aria-label={`${ariaLabelPrefix} ${index + 1} of ${length}`}
          aria-invalid={effectiveError ? "true" : undefined}
          aria-describedby={ariaDescribedBy}
          onChange={(e) => handleInputChange(e, index)}
          onKeyDown={(e) => handleKeyDown(e, index)}
          onPaste={handlePaste}
          className={`w-11 h-12 text-center text-lg font-bold rounded-lg border focus:outline-none focus:ring-2 focus:ring-offset-1 transition-all ${
            effectiveError
              ? "ux4g-border-error ux4g-bg-neutral-soft ux4g-text-error"
              : "ux4g-border-neutral-subtle ux4g-bg-neutral-elevated hover:ux4g-border-neutral-strong focus:ux4g-border-primary"
          } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        />
      ))}
    </div>
  );
};
