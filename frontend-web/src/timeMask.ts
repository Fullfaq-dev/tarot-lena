/**
 * Маска для поля «время рождения»: оставляет только цифры и ставит двоеточие после часов (14:30).
 * Если час однозначный и человек сам поставил разделитель (9:05, 9.05, 9 05), час дополняется нулём → 09:05.
 */
export function maskTime(raw: string): string {
  const withSeparator = raw.match(/^\D*(\d{1,2})[^\d]+(\d{0,2})/);
  if (withSeparator) {
    return `${withSeparator[1].padStart(2, "0")}:${withSeparator[2]}`;
  }
  const digits = raw.replace(/\D/g, "").slice(0, 4);
  if (digits.length <= 2) return digits;
  return `${digits.slice(0, 2)}:${digits.slice(2)}`;
}

export const TIME_PLACEHOLDER = "чч:мм, например 14:30";
