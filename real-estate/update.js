const fs = require('fs');
let data = fs.readFileSync('index.html', 'utf8');
data = data.replace('href=" /favicon.svg\', 'href=\/lc-logo.png\');
data = data.replace('type=\image/svg+xml\', 'type=\image/png\');
fs.writeFileSync('index.html', data);
