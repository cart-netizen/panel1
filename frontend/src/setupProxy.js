const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Проксируем только API запросы, исключая webpack файлы
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://127.0.0.1:8002',
      changeOrigin: true,
      logLevel: 'debug', // Для отладки, потом можно убрать
    })
  );};