interface RequiredFieldProps {
  label: string;
  children: React.ReactNode;
}

export function RequiredField({ label, children }: RequiredFieldProps) {
  return (
    <>
      <label className="text-[10px] font-semibold text-gray-500 uppercase">
        {label} <span className="text-red-500">*</span>
      </label>
      <div className="mt-1">{children}</div>
    </>
  );
}
