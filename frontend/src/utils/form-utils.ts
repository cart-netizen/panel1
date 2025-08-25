// frontend/src/utils/form-utils.ts
export const validateEmail = (email: string): boolean => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

export const validatePassword = (password: string): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (password.length < 6) {
    errors.push('Пароль должен содержать минимум 6 символов');
  }

  if (!/(?=.*[a-z])/.test(password)) {
    errors.push('Пароль должен содержать строчные буквы');
  }

  if (!/(?=.*[A-Z])/.test(password)) {
    errors.push('Пароль должен содержать заглавные буквы');
  }

  if (!/(?=.*\d)/.test(password)) {
    errors.push('Пароль должен содержать цифры');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
};

export const sanitizeInput = (input: string): string => {
  return input.trim().replace(/[<>]/g, '');
};

export const formatPhoneNumber = (phone: string): string => {
  const cleaned = phone.replace(/\D/g, '');
  const match = cleaned.match(/^(\d{1})(\d{3})(\d{3})(\d{2})(\d{2})$/);

  if (match) {
    return `+${match[1]} (${match[2]}) ${match[3]}-${match[4]}-${match[5]}`;
  }

  return phone;
};