// import { useEffect } from 'react';
// import { apiClient } from '../services/api';
//
// export const useTokenRefresh = () => {
//   useEffect(() => {
//     // Обновляем токен каждые 20 минут
//     const refreshInterval = setInterval(async () => {
//       const token = localStorage.getItem('access_token');
//       if (token) {
//         const refreshed = await apiClient.refreshToken();
//         if (!refreshed) {
//           console.warn('Failed to refresh token');
//         }
//       }
//     }, 20 * 60 * 1000); // 20 минут
//
//     return () => clearInterval(refreshInterval);
//   }, []);
// };