import React from 'react';

type Props = {
  label: string;
  onClick: () => void;
};

export function ActionButton({ label, onClick }: Props) {
  return (
    <button className="action-button" onClick={onClick}>
      {label}
    </button>
  );
}
