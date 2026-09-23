const fs = require('fs');
const path = require('path');

// Create simple SVG icons and convert to PNG-like data URLs for Chrome extension
// Since we can't use external libraries, we'll create simple colored squares as placeholders

const sizes = [16, 48, 128];
const iconsDir = path.join(__dirname, '..', 'dist', 'icons');

// Ensure icons directory exists
if (!fs.existsSync(iconsDir)) {
  fs.mkdirSync(iconsDir, { recursive: true });
}

// Create simple PNG files (1x1 pixel scaled up - Chrome will handle it)
// These are minimal valid PNG files with solid colors
sizes.forEach(size => {
  const filePath = path.join(iconsDir, `icon${size}.png`);
  
  // Create a simple valid PNG file (green color #4CAF50)
  // This is a minimal 1x1 PNG that browsers can scale
  const pngData = Buffer.from([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, // PNG signature
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, // IHDR chunk
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, // 1x1 pixel
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, // 8-bit RGB
    0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41, // IDAT chunk
    0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00, // compressed data (green)
    0x00, 0x03, 0x01, 0x01, 0x00, 0x18, 0xDD, 0x8D,
    0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, // IEND chunk
    0x44, 0xAE, 0x42, 0x60, 0x82
  ]);
  
  fs.writeFileSync(filePath, pngData);
  console.log(`Created icon${size}.png`);
});

console.log('Icons created successfully!');
