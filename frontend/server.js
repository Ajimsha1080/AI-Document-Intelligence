const next = require('next');
const http = require('http');

const port = parseInt(process.env.PORT || '3005', 10);
const app = next({ dev: true, dir: __dirname });
const handle = app.getRequestHandler();

app.prepare().then(() => {
  const server = http.createServer((req, res) => {
    handle(req, res);
  });
  server.listen(port, '0.0.0.0', (err) => {
    if (err) {
      console.error(`Failed to start server on port ${port}:`, err);
      process.exit(1);
    }
    console.log(`> Sanad DocIntel UAE Sovereign Platform Ready on http://localhost:${port}`);
  });
});
