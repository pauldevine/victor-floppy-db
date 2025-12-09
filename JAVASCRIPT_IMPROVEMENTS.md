# JavaScript Modernization Recommendations

## Current State Analysis

The current JavaScript in `floppies/static/floppies/functions.js` uses:
- `var` declarations (ES5)
- Vanilla DOM manipulation
- No error handling
- No module system

## Recommended Improvements

### 1. Modern JavaScript Syntax (ES6+)

**Current Code:**
```javascript
function reorderSelectedOptions(selectId) {
    var select = document.getElementById(selectId);

    function reorder() {
        var selectedOptions = [];
        var unselectedOptions = [];

        for (var i = 0; i < select.options.length; i++) {
            if (select.options[i].selected) {
                selectedOptions.push(select.options[i]);
            } else {
                unselectedOptions.push(select.options[i]);
            }
        }
        // ...
    }
}
```

**Recommended Modernization:**
```javascript
function reorderSelectedOptions(selectId) {
    const select = document.getElementById(selectId);

    if (!select) {
        console.error(`Select element with id '${selectId}' not found`);
        return;
    }

    function reorder() {
        const optionsArray = Array.from(select.options);
        const selectedOptions = optionsArray.filter(opt => opt.selected);
        const unselectedOptions = optionsArray.filter(opt => !opt.selected);

        // Sort using localeCompare for proper internationalization
        const sortByText = (a, b) => a.text.localeCompare(b.text, undefined, {sensitivity: 'base'});

        selectedOptions.sort(sortByText);
        unselectedOptions.sort(sortByText);

        // Clear and repopulate
        select.innerHTML = '';
        [...selectedOptions, ...unselectedOptions].forEach(option => {
            select.appendChild(option);
        });
    }

    // Initial reorder
    reorder();

    // Add event listener
    select.addEventListener('change', reorder, {passive: true});
}
```

**Benefits:**
- `const`/`let` instead of `var` (block scoping, immutability)
- Error handling (prevents crashes if element not found)
- `Array.from()` and array methods (more readable)
- `localeCompare()` for proper sorting
- Spread operator (`...`) for cleaner code
- Event listener options (performance hint)

### 2. Add Error Handling

**Current:** No error handling - failures are silent

**Recommended:**
```javascript
try {
    const select = document.getElementById(selectId);
    if (!select) {
        throw new Error(`Select element '${selectId}' not found`);
    }
    // ... rest of code
} catch (error) {
    console.error('Error in reorderSelectedOptions:', error);
    // Optionally report to error tracking service
}
```

### 3. Add Input Validation

**Recommended:**
```javascript
function reorderSelectedOptions(selectId) {
    if (typeof selectId !== 'string' || !selectId.trim()) {
        console.warn('Invalid selectId provided to reorderSelectedOptions');
        return;
    }
    // ... rest of code
}
```

### 4. Performance Optimization

**Current:** Uses `innerHTML = ''` which can be slow

**Recommended:**
```javascript
// More efficient clearing
while (select.firstChild) {
    select.removeChild(select.firstChild);
}

// Or use modern approach
select.replaceChildren(...selectedOptions, ...unselectedOptions);
```

### 5. Add JSDoc Comments

**Recommended:**
```javascript
/**
 * Reorders options in a select element, placing selected options first
 * and sorting all options alphabetically.
 *
 * @param {string} selectId - The ID of the select element to reorder
 * @throws {Error} If the select element is not found
 * @example
 * reorderSelectedOptions('id_subjects');
 */
function reorderSelectedOptions(selectId) {
    // ... implementation
}
```

### 6. Module Organization

**Current:** Global functions

**Recommended:** Use ES6 modules
```javascript
// floppies-utils.js
export function reorderSelectedOptions(selectId) {
    // ... implementation
}

export function initializeMultiSelects(selectIds) {
    selectIds.forEach(id => {
        reorderSelectedOptions(id);
    });
}

// main.js
import { initializeMultiSelects } from './floppies-utils.js';

document.addEventListener('DOMContentLoaded', () => {
    initializeMultiSelects([
        'id_subjects',
        'id_creators',
        'id_contributors',
        'id_collections',
        'id_photos'
    ]);
});
```

### 7. Add Unit Tests

**Recommended:** Use Jest or Vitest
```javascript
// functions.test.js
describe('reorderSelectedOptions', () => {
    let select;

    beforeEach(() => {
        select = document.createElement('select');
        select.id = 'test-select';
        select.multiple = true;
        document.body.appendChild(select);
    });

    afterEach(() => {
        document.body.removeChild(select);
    });

    test('should sort selected options first', () => {
        select.innerHTML = `
            <option value="1">Zebra</option>
            <option value="2" selected>Apple</option>
            <option value="3">Banana</option>
            <option value="4" selected>Cat</option>
        `;

        reorderSelectedOptions('test-select');

        const options = Array.from(select.options);
        expect(options[0].text).toBe('Apple');
        expect(options[1].text).toBe('Cat');
        expect(options[0].selected).toBe(true);
        expect(options[1].selected).toBe(true);
    });

    test('should handle missing element gracefully', () => {
        expect(() => {
            reorderSelectedOptions('nonexistent');
        }).not.toThrow();
    });
});
```

### 8. Accessibility Improvements

**Recommended:**
```javascript
function reorderSelectedOptions(selectId) {
    const select = document.getElementById(selectId);

    if (!select) return;

    // Announce changes to screen readers
    const announceReorder = () => {
        const selectedCount = Array.from(select.options).filter(opt => opt.selected).length;
        const liveRegion = document.getElementById('aria-live-region') || createLiveRegion();
        liveRegion.textContent = `${selectedCount} items selected and reordered`;
    };

    function reorder() {
        // ... existing reorder code
        announceReorder();
    }

    // ... rest of code
}

function createLiveRegion() {
    const region = document.createElement('div');
    region.id = 'aria-live-region';
    region.setAttribute('aria-live', 'polite');
    region.setAttribute('aria-atomic', 'true');
    region.className = 'sr-only';  // Visually hidden but accessible
    document.body.appendChild(region);
    return region;
}
```

### 9. Build Tools & Bundling

**Current:** Raw JS files loaded directly

**Recommended:** Use modern build tools

```javascript
// package.json
{
  "scripts": {
    "build": "webpack --mode production",
    "dev": "webpack --mode development --watch",
    "test": "jest"
  },
  "devDependencies": {
    "@babel/core": "^7.23.0",
    "@babel/preset-env": "^7.23.0",
    "babel-loader": "^9.1.3",
    "webpack": "^5.89.0",
    "webpack-cli": "^5.1.4",
    "jest": "^29.7.0"
  }
}
```

```javascript
// webpack.config.js
module.exports = {
    entry: './floppies/static/src/main.js',
    output: {
        path: path.resolve(__dirname, 'floppies/static/dist'),
        filename: 'bundle.js'
    },
    module: {
        rules: [
            {
                test: /\.js$/,
                exclude: /node_modules/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        presets: ['@babel/preset-env']
                    }
                }
            }
        ]
    }
};
```

### 10. TypeScript (Optional but Recommended)

**Benefits:**
- Type safety
- Better IDE autocomplete
- Catch errors at compile time
- Self-documenting code

```typescript
// functions.ts
interface SelectOption extends HTMLOptionElement {
    text: string;
    value: string;
    selected: boolean;
}

function reorderSelectedOptions(selectId: string): void {
    const select = document.getElementById(selectId) as HTMLSelectElement | null;

    if (!select) {
        console.error(`Select element '${selectId}' not found`);
        return;
    }

    function reorder(): void {
        const options: SelectOption[] = Array.from(select.options);
        const [selected, unselected] = partition(options, opt => opt.selected);

        const sortByText = (a: SelectOption, b: SelectOption): number =>
            a.text.localeCompare(b.text, undefined, { sensitivity: 'base' });

        selected.sort(sortByText);
        unselected.sort(sortByText);

        select.replaceChildren(...selected, ...unselected);
    }

    reorder();
    select.addEventListener('change', reorder, { passive: true });
}

function partition<T>(array: T[], predicate: (item: T) => boolean): [T[], T[]] {
    return array.reduce(
        ([pass, fail], item) => predicate(item)
            ? [[...pass, item], fail]
            : [pass, [...fail, item]],
        [[], []] as [T[], T[]]
    );
}
```

## Implementation Priority

1. **High Priority (Do First):**
   - Replace `var` with `const`/`let`
   - Add error handling
   - Add input validation
   - Fix sorting to use `localeCompare()`

2. **Medium Priority:**
   - Add JSDoc comments
   - Modularize code
   - Add accessibility features
   - Write unit tests

3. **Low Priority (Nice to Have):**
   - Set up build tooling
   - Consider TypeScript
   - Add performance monitoring
   - Implement code splitting

## Browser Compatibility

All recommended changes use features available in:
- Chrome 51+
- Firefox 54+
- Safari 10+
- Edge 15+

For older browsers, use Babel to transpile ES6+ to ES5.

## Security Considerations

1. **XSS Prevention:**
   - Never use `innerHTML` with user input
   - Use `textContent` or `createElement()` instead
   - Sanitize any dynamic content

2. **Content Security Policy:**
   - Avoid inline scripts
   - Use external JS files
   - Consider adding CSP headers

## Resources

- [MDN Web Docs - JavaScript](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
- [Modern JavaScript Tutorial](https://javascript.info/)
- [You Don't Know JS](https://github.com/getify/You-Dont-Know-JS)
- [Clean Code JavaScript](https://github.com/ryanmcdermott/clean-code-javascript)

## Conclusion

While the current JavaScript is functional, implementing these improvements would provide:
- Better maintainability
- Improved performance
- Enhanced accessibility
- Easier testing
- Better developer experience
- Future-proofing

Start with high-priority items for immediate benefits, then progressively enhance as time allows.
