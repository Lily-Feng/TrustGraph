import { existsSync, readFileSync, statSync } from 'node:fs';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(scriptDirectory, '..', '..');
const requiredFiles = ['index.html', 'style.css', 'app.js'];
const errors = [];

for (const file of requiredFiles) {
  const path = resolve(repositoryRoot, file);
  if (!existsSync(path) || !statSync(path).isFile() || statSync(path).size === 0) {
    errors.push(`Required site file is missing or empty: ${file}`);
  }
}

if (errors.length === 0) {
  const html = readFileSync(resolve(repositoryRoot, 'index.html'), 'utf8');
  const css = readFileSync(resolve(repositoryRoot, 'style.css'), 'utf8');
  const references = [];

  for (const match of html.matchAll(/\b(?:src|href)\s*=\s*["']([^"']+)["']/giu)) {
    references.push(match[1]);
  }

  for (const match of css.matchAll(/url\(\s*["']?([^"')]+)["']?\s*\)/giu)) {
    references.push(match[1]);
  }

  for (const reference of references) {
    if (/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/iu.test(reference)) {
      continue;
    }

    const pathPart = decodeURIComponent(reference.split(/[?#]/u, 1)[0]);
    if (!pathPart) {
      continue;
    }

    if (isAbsolute(pathPart)) {
      errors.push(`Root-relative reference will break on a project Pages site: ${reference}`);
      continue;
    }

    const target = resolve(repositoryRoot, pathPart);
    const relativeTarget = relative(repositoryRoot, target);
    if (relativeTarget === '..' || relativeTarget.startsWith(`..${sep}`)) {
      errors.push(`Reference escapes the repository: ${reference}`);
    } else if (!existsSync(target) || !statSync(target).isFile()) {
      errors.push(`Local reference does not resolve to a file: ${reference}`);
    }
  }
}

if (errors.length > 0) {
  console.error(errors.map((error) => `- ${error}`).join('\n'));
  process.exit(1);
}

console.log('Static site validation passed.');
