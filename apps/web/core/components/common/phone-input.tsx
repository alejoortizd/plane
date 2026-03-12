"use client";

import React from "react";
import PhoneInputBase from "react-phone-number-input";
import type { Value } from "react-phone-number-input";

type Props = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  defaultCountry?: "CO" | "US" | "MX" | "ES" | "AR" | "CL" | "PE" | "EC" | "VE" | "BR";
  disabled?: boolean;
  className?: string;
};

export const PhoneInput: React.FC<Props> = ({
  value,
  onChange,
  placeholder = "+57 300 123 4567",
  defaultCountry = "CO",
  disabled = false,
  className = "",
}) => (
  <PhoneInputBase
    international
    countryCallingCodeEditable={false}
    defaultCountry={defaultCountry}
    value={(value as Value) || undefined}
    onChange={(val) => onChange(val || "")}
    placeholder={placeholder}
    disabled={disabled}
    className={`plane-phone-input ${className}`}
  />
);
