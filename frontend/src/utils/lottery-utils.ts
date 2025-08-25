// frontend/src/utils/lottery-utils.ts
export const validateCombination = (combination: number[], max: number): boolean => {
  return combination.every(num => num >= 1 && num <= max);
};

export const formatCombination = (combination: number[]): string => {
  return combination.sort((a, b) => a - b).join(', ');
};

export const calculateWinProbability = (field1Size: number, field1Max: number, field2Size: number, field2Max: number): number => {
  const combination1 = factorial(field1Max) / (factorial(field1Size) * factorial(field1Max - field1Size));
  const combination2 = factorial(field2Max) / (factorial(field2Size) * factorial(field2Max - field2Size));
  return 1 / (combination1 * combination2);
};

const factorial = (n: number): number => {
  if (n <= 1) return 1;
  return n * factorial(n - 1);
};