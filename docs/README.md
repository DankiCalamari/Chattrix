# Chattrix Documentation

This directory contains the complete documentation for Chattrix, designed to be hosted on GitHub Pages.

## 📁 Documentation Structure

```
docs/
├── _config.yml              # GitHub Pages configuration
├── index.md                 # Documentation homepage
├── getting-started.md       # Quick start guide
├── installation.md          # Installation instructions
├── configuration.md         # Configuration guide
├── deployment.md            # Production deployment
├── api-reference.md         # API documentation
├── user-guide.md           # User manual
├── troubleshooting.md      # Common issues & solutions
├── contributing.md         # Contribution guidelines
├── faq.md                  # Frequently asked questions
└── assets/                 # Images and other assets
    └── images/
```

## 🚀 Setting up GitHub Pages

### 1. Enable GitHub Pages

1. Go to your repository settings
2. Scroll to "Pages" section
3. Select source: "Deploy from a branch"
4. Choose branch: `main` or `master`
5. Select folder: `/docs`
6. Click "Save"

### 2. Custom Domain (Optional)

1. Add a `CNAME` file to the `/docs` directory
2. Add your domain name (e.g., `docs.chattrix.com`)
3. Configure DNS records at your domain provider

### 3. Theme Customization

The documentation uses the Cayman theme. You can customize it by:

1. **Editing `_config.yml`** for site-wide settings
2. **Modifying CSS** by adding custom styles
3. **Customizing layouts** by overriding theme files

## 📝 Contributing to Documentation

### Adding New Pages

1. Create a new `.md` file in the `/docs` directory
2. Add front matter with title and layout:
   ```yaml
   ---
   layout: default
   title: Page Title
   ---
   ```
3. Update navigation in `_config.yml` if needed
4. Link to the new page from relevant sections

### Editing Existing Pages

1. Edit the appropriate `.md` file
2. Follow the existing style and structure
3. Test locally using Jekyll (optional)
4. Submit a pull request

### Style Guide

- **Use clear headings** - Organize content with H1-H6
- **Include code examples** - Show practical implementation
- **Add navigation links** - Help users find related content
- **Keep it concise** - Break up large sections
- **Use callouts** - Highlight important information

### Markdown Features

```markdown
# Headers
## Sub-headers
### Sub-sub-headers

**Bold text**
*Italic text*
`Inline code`

```code blocks```

> Blockquotes for important notes

- Bullet lists
1. Numbered lists

[Links](page.md)
![Images](assets/images/screenshot.png)

| Tables | Work | Too |
|--------|------|-----|
| Col 1  | Col 2| Col 3|
```

## 🔧 Local Development

### Prerequisites

- Ruby 2.7+
- Bundler
- Jekyll

### Setup

```bash
# Install dependencies
cd docs
bundle install

# Run local server
bundle exec jekyll serve

# Open browser to http://localhost:4000
```

### Configuration

Edit `_config.yml` to customize:
- Site title and description
- Navigation menu
- Theme settings
- Social links
- SEO settings

## 📊 Analytics & Monitoring

### Google Analytics

Add to `_config.yml`:
```yaml
google_analytics: GA_MEASUREMENT_ID
```

### Search Engine Optimization

The documentation includes:
- **jekyll-seo-tag** plugin
- **Sitemap generation**
- **Proper meta tags**
- **Structured data**

## 🎨 Customization

### Custom CSS

Add custom styles in `assets/css/style.scss`:

```scss
---
---

@import "{{ site.theme }}";

/* Custom styles */
.custom-class {
    color: #333;
    background: #f5f5f5;
}

/* Override theme variables */
$primary-color: #0066cc;
$secondary-color: #f39c12;
```

### Custom Layouts

Override theme layouts by creating files in `_layouts/`:

```html
<!-- _layouts/custom.html -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ page.title }} - {{ site.title }}</title>
</head>
<body>
    {{ content }}
</body>
</html>
```

### Adding Images

1. Add images to `assets/images/`
2. Reference in markdown:
   ```markdown
   ![Alt text](assets/images/screenshot.png)
   ```
3. Optimize images for web (compress, resize)

## 📱 Mobile Optimization

The documentation is mobile-friendly:
- **Responsive design** - Works on all screen sizes
- **Touch-friendly navigation** - Easy mobile browsing
- **Fast loading** - Optimized for mobile networks
- **Progressive enhancement** - Works without JavaScript

## 🔍 Search Functionality

### Enabling Search

Add search functionality:

1. **Simple search** with JavaScript
2. **Algolia search** for advanced features
3. **Google Custom Search** for easy setup

### Example JavaScript Search

```javascript
// Add to assets/js/search.js
function searchDocs() {
    const query = document.getElementById('search-input').value.toLowerCase();
    const results = pages.filter(page => 
        page.title.toLowerCase().includes(query) ||
        page.content.toLowerCase().includes(query)
    );
    displayResults(results);
}
```

## 📈 Best Practices

### Content Organization

- **Logical hierarchy** - Clear information architecture
- **Cross-references** - Link related content
- **Progressive disclosure** - Start simple, add detail
- **User-focused** - Write for your audience

### Writing Style

- **Clear language** - Avoid jargon and acronyms
- **Active voice** - More engaging and direct
- **Short paragraphs** - Easier to scan and read
- **Consistent tone** - Professional but friendly

### Maintenance

- **Regular updates** - Keep content current
- **Link checking** - Verify external links work
- **User feedback** - Listen to documentation users
- **Version control** - Track changes and updates

## 🤝 Community

### Getting Help

- **GitHub Issues** - Report documentation problems
- **Discussions** - Ask questions about documentation
- **Discord** - Real-time help and feedback

### Contributing

We welcome documentation contributions:
- **Fix typos** - Small improvements help everyone
- **Add examples** - Show real-world usage
- **Improve clarity** - Make explanations clearer
- **Add translations** - Help non-English speakers

## 📞 Support

For documentation-specific issues:
- **GitHub Issues** - Bug reports and suggestions
- **Pull Requests** - Direct improvements
- **Discussions** - Questions and ideas

For general Chattrix support, see the main documentation.

---

**Visit the live documentation:** [https://DankiCalamari.github.io/Chattrix](https://DankiCalamari.github.io/Chattrix)

*Last updated: August 2025*
