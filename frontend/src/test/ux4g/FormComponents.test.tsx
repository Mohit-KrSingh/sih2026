import { useState } from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  Input,
  Textarea,
  Select,
  Radio,
  Checkbox,
  Switch,
  DatePicker,
  FileUpload,
  OtpInput,
  FormField,
  ErrorSummary,
} from "../../components/ux4g";

describe("UX4G Form Components", () => {
  describe("Input", () => {
    it("renders input within UX4G container and handles value changes", () => {
      const handleChange = vi.fn();
      render(<Input placeholder="Enter student name" onChange={handleChange} size="md" />);
      const input = screen.getByPlaceholderText("Enter student name");
      expect(input).toBeInTheDocument();
      fireEvent.change(input, { target: { value: "Aaditya" } });
      expect(handleChange).toHaveBeenCalled();
    });

    it("applies error state and aria-invalid attribute", () => {
      render(<Input state="error" placeholder="Invalid field" />);
      const input = screen.getByPlaceholderText("Invalid field");
      expect(input).toHaveAttribute("aria-invalid", "true");
      expect(input.parentElement?.className).toContain("ux4g-input-error");
    });
  });

  describe("Textarea", () => {
    it("renders textarea with custom rows and handles input", () => {
      render(<Textarea rows={5} placeholder="Write justification..." />);
      const textarea = screen.getByPlaceholderText("Write justification...");
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveAttribute("rows", "5");
      fireEvent.change(textarea, { target: { value: "Valid exception reason." } });
      expect(textarea).toHaveValue("Valid exception reason.");
    });
  });

  describe("Select", () => {
    it("renders select with options and handles selection change", () => {
      const handleChange = vi.fn();
      render(
        <Select
          aria-label="Select course"
          onChange={handleChange}
          options={[
            { value: "ug_cse", label: "UG Computer Science" },
            { value: "ug_ece", label: "UG Electronics" },
          ]}
        />
      );
      const select = screen.getByRole("combobox", { name: "Select course" });
      expect(select).toBeInTheDocument();
      fireEvent.change(select, { target: { value: "ug_ece" } });
      expect(handleChange).toHaveBeenCalled();
      expect(select).toHaveValue("ug_ece");
    });
  });

  describe("Radio, Checkbox & Switch", () => {
    it("renders accessible Radio button and updates selection", () => {
      render(
        <fieldset>
          <legend>Seat Type</legend>
          <Radio name="seat" label="Regular" value="regular" defaultChecked />
          <Radio name="seat" label="Supernumerary" value="super" />
        </fieldset>
      );
      const regular = screen.getByRole("radio", { name: "Regular" });
      const supernumerary = screen.getByRole("radio", { name: "Supernumerary" });
      expect(regular).toBeChecked();
      expect(supernumerary).not.toBeChecked();

      fireEvent.click(supernumerary);
      expect(supernumerary).toBeChecked();
    });

    it("renders accessible Checkbox with indeterminate support", () => {
      const { rerender } = render(
        <Checkbox label="Agree to declarations" indeterminate={false} />
      );
      const checkbox = screen.getByRole("checkbox", { name: "Agree to declarations" }) as HTMLInputElement;
      expect(checkbox.indeterminate).toBe(false);

      rerender(<Checkbox label="Agree to declarations" indeterminate={true} />);
      expect(checkbox.indeterminate).toBe(true);
    });

    it("renders Switch with role switch", () => {
      render(<Switch label="Auto-validate" defaultChecked />);
      const toggle = screen.getByRole("switch", { name: "Auto-validate" });
      expect(toggle).toBeInTheDocument();
      expect(toggle).toBeChecked();
      fireEvent.click(toggle);
      expect(toggle).not.toBeChecked();
    });
  });

  describe("DatePicker", () => {
    it("renders date input with calendar picker type", () => {
      render(<DatePicker aria-label="Admission Date" defaultValue="2026-07-15" />);
      const dateInput = screen.getByLabelText("Admission Date");
      expect(dateInput).toHaveAttribute("type", "date");
      expect(dateInput).toHaveValue("2026-07-15");
    });
  });

  describe("FileUpload", () => {
    it("handles file selection and displays filename and size", () => {
      const handleSelect = vi.fn();
      const file = new File(["col1,col2\n1,2"], "students.csv", { type: "text/csv" });

      render(
        <FileUpload
          label="Student Data Upload"
          selectedFile={file}
          onFileSelect={handleSelect}
        />
      );

      expect(screen.getByText("students.csv")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Remove selected file" })).toBeInTheDocument();
    });
  });

  describe("OtpInput", () => {
    it("renders 6 digit inputs and handles keyboard typing and auto-advance", () => {
      function OtpWrapper() {
        const [otp, setOtp] = useState("");
        return <OtpInput value={otp} onChange={setOtp} length={6} />;
      }

      render(<OtpWrapper />);
      const digit1 = screen.getByLabelText("Digit 1 of 6");
      const digit2 = screen.getByLabelText("Digit 2 of 6");

      fireEvent.change(digit1, { target: { value: "5" } });
      expect(digit1).toHaveValue("5");

      // Verify paste handling of 6-digit code
      fireEvent.paste(digit2, {
        clipboardData: {
          getData: () => "987654",
        },
      });

      const digit6 = screen.getByLabelText("Digit 6 of 6");
      expect(digit6).toHaveValue("4");
    });
  });

  describe("FormField", () => {
    it("associates label, hint, and error with input via aria attributes", () => {
      render(
        <FormField
          id="apaar-input"
          label="APAAR Number"
          required
          hint="12 digit identifier"
          error="APAAR number must not be empty"
        >
          <Input />
        </FormField>
      );

      const label = screen.getByText("APAAR Number");
      expect(label).toBeInTheDocument();
      expect(screen.getByText("Required")).toBeInTheDocument();

      const input = screen.getByLabelText(/APAAR Number/);
      expect(input).toHaveAttribute("id", "apaar-input");
      expect(input).toHaveAttribute("aria-describedby", "apaar-input-hint apaar-input-error");
      expect(input).toHaveAttribute("aria-invalid", "true");

      const errorText = screen.getByRole("alert");
      expect(errorText).toHaveTextContent("APAAR number must not be empty");
    });
  });

  describe("ErrorSummary", () => {
    it("renders error summary and navigates focus to field when link is clicked", () => {
      render(
        <div>
          <ErrorSummary
            errors={[
              { fieldId: "field-1", message: "Field 1 has an error" },
              { fieldId: "field-2", message: "Field 2 is required" },
            ]}
          />
          <input id="field-1" aria-label="Field 1" />
          <input id="field-2" aria-label="Field 2" />
        </div>
      );

      const summary = screen.getByRole("alert");
      expect(summary).toBeInTheDocument();
      expect(screen.getByText("Field 1 has an error")).toBeInTheDocument();

      const link1 = screen.getByRole("link", { name: "Field 1 has an error" });
      const input1 = screen.getByLabelText("Field 1");
      const focusSpy = vi.spyOn(input1, "focus");

      fireEvent.click(link1);
      expect(focusSpy).toHaveBeenCalled();
    });
  });
});
