const next = require('next');
const http = require('http');
const fs = require('fs');
const path = require('path');

const port = parseInt(process.env.PORT || '3005', 10);
const hasBuild = fs.existsSync(path.join(__dirname, '.next', 'BUILD_ID'));
const dev = process.env.NODE_ENV === 'development' ? true : !hasBuild;
const app = next({ dev, dir: __dirname });
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
    console.log(`> Sanad DocIntel UAE Sovereign Platform Ready on http://localhost:${port} (mode: ${dev ? 'dev' : 'production'})`);
  });
});
