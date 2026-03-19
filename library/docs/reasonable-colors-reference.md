# Reasonable Colors — Quick Reference

Source: `unpkg.com/reasonable-colors@0.4.0/reasonable-colors.css`
Install: `npm install reasonable-colors`
Docs: https://www.reasonable.work/colors/

---

## Contrast Rules

Shade differences guarantee WCAG contrast ratios across all colour sets:

| Shade diff | Contrast ratio | WCAG level        |
|-----------|----------------|-------------------|
| 2         | ≥ 3:1          | AA large text/UI  |
| 3         | ≥ 4.5:1        | AA body text      |
| 4         | ≥ 7:1          | AAA               |

The `color` spelling in CSS variable names is the library's convention — acceptable despite British spelling preference elsewhere.

---

## Usage Pattern

```css
@import 'reasonable-colors'; /* or link CDN */

:root {
  /* Map RC vars to semantic roles */
  --color-primary:    var(--color-azure-3);
  --color-primary-bg: var(--color-azure-1);
  --color-on-primary: var(--color-azure-6);
}

/* Components reference semantic vars only */
.button { background: var(--color-primary); }
```

---

## Colour Reference

Variable format: `--color-{name}-{shade}` where shade is 1 (lightest) → 6 (darkest).

### Gray

| Shade | Hex       |
|-------|-----------|
| 1     | `#f6f6f6` |
| 2     | `#e2e2e2` |
| 3     | `#8b8b8b` |
| 4     | `#6f6f6f` |
| 5     | `#3e3e3e` |
| 6     | `#222222` |

### Rose

| Shade | Hex       |
|-------|-----------|
| 1     | `#fff7f9` |
| 2     | `#ffdce5` |
| 3     | `#ff3b8d` |
| 4     | `#db0072` |
| 5     | `#800040` |
| 6     | `#4c0023` |

### Raspberry

| Shade | Hex       |
|-------|-----------|
| 1     | `#fff8f8` |
| 2     | `#ffdddf` |
| 3     | `#ff426c` |
| 4     | `#de0051` |
| 5     | `#82002c` |
| 6     | `#510018` |

### Red

| Shade | Hex       |
|-------|-----------|
| 1     | `#fff8f6` |
| 2     | `#ffddd8` |
| 3     | `#ff4647` |
| 4     | `#e0002b` |
| 5     | `#830014` |
| 6     | `#530003` |

### Orange

| Shade | Hex       |
|-------|-----------|
| 1     | `#fff8f5` |
| 2     | `#ffded1` |
| 3     | `#fd4d00` |
| 4     | `#cd3c00` |
| 5     | `#752100` |
| 6     | `#401600` |

### Cinnamon

| Shade | Hex       |
|-------|-----------|
| 1     | `#fff8f3` |
| 2     | `#ffdfc6` |
| 3     | `#d57300` |
| 4     | `#ac5c00` |
| 5     | `#633300` |
| 6     | `#371d00` |

### Amber

| Shade | Hex       |
|-------|-----------|
| 1     | `#fff8ef` |
| 2     | `#ffe0b2` |
| 3     | `#b98300` |
| 4     | `#926700` |
| 5     | `#523800` |
| 6     | `#302100` |

### Yellow

| Shade | Hex       |
|-------|-----------|
| 1     | `#fff9e5` |
| 2     | `#ffe53e` |
| 3     | `#9c8b00` |
| 4     | `#7d6f00` |
| 5     | `#463d00` |
| 6     | `#292300` |

### Lime

| Shade | Hex       |
|-------|-----------|
| 1     | `#f7ffac` |
| 2     | `#d5f200` |
| 3     | `#819300` |
| 4     | `#677600` |
| 5     | `#394100` |
| 6     | `#222600` |

### Chartreuse

| Shade | Hex       |
|-------|-----------|
| 1     | `#e5ffc3` |
| 2     | `#98fb00` |
| 3     | `#5c9b00` |
| 4     | `#497c00` |
| 5     | `#264500` |
| 6     | `#182600` |

### Green

| Shade | Hex       |
|-------|-----------|
| 1     | `#e0ffd9` |
| 2     | `#72ff6c` |
| 3     | `#00a21f` |
| 4     | `#008217` |
| 5     | `#004908` |
| 6     | `#062800` |

### Emerald

| Shade | Hex       |
|-------|-----------|
| 1     | `#dcffe6` |
| 2     | `#5dffa2` |
| 3     | `#00a05a` |
| 4     | `#008147` |
| 5     | `#004825` |
| 6     | `#002812` |

### Aquamarine

| Shade | Hex       |
|-------|-----------|
| 1     | `#daffef` |
| 2     | `#42ffc6` |
| 3     | `#009f78` |
| 4     | `#007f5f` |
| 5     | `#004734` |
| 6     | `#00281b` |

### Teal

| Shade | Hex       |
|-------|-----------|
| 1     | `#d7fff7` |
| 2     | `#00ffe4` |
| 3     | `#009e8c` |
| 4     | `#007c6e` |
| 5     | `#00443c` |
| 6     | `#002722` |

### Cyan

| Shade | Hex       |
|-------|-----------|
| 1     | `#c4fffe` |
| 2     | `#00fafb` |
| 3     | `#00999a` |
| 4     | `#007a7b` |
| 5     | `#004344` |
| 6     | `#002525` |

### Powder

| Shade | Hex       |
|-------|-----------|
| 1     | `#dafaff` |
| 2     | `#8df0ff` |
| 3     | `#0098a9` |
| 4     | `#007987` |
| 5     | `#004048` |
| 6     | `#002227` |

### Sky

| Shade | Hex       |
|-------|-----------|
| 1     | `#e3f7ff` |
| 2     | `#aee9ff` |
| 3     | `#0094b4` |
| 4     | `#007590` |
| 5     | `#00404f` |
| 6     | `#001f28` |

### Cerulean

| Shade | Hex       |
|-------|-----------|
| 1     | `#e8f6ff` |
| 2     | `#b9e3ff` |
| 3     | `#0092c5` |
| 4     | `#00749d` |
| 5     | `#003c54` |
| 6     | `#001d2a` |

### Azure

| Shade | Hex       |
|-------|-----------|
| 1     | `#e8f2ff` |
| 2     | `#c6e0ff` |
| 3     | `#008fdb` |
| 4     | `#0071af` |
| 5     | `#003b5e` |
| 6     | `#001c30` |

### Blue

| Shade | Hex       |
|-------|-----------|
| 1     | `#f0f4ff` |
| 2     | `#d4e0ff` |
| 3     | `#0089fc` |
| 4     | `#006dca` |
| 5     | `#00386d` |
| 6     | `#001a39` |

### Indigo

| Shade | Hex       |
|-------|-----------|
| 1     | `#f3f3ff` |
| 2     | `#deddff` |
| 3     | `#657eff` |
| 4     | `#0061fc` |
| 5     | `#00328a` |
| 6     | `#001649` |

### Violet

| Shade | Hex       |
|-------|-----------|
| 1     | `#f7f1ff` |
| 2     | `#e8daff` |
| 3     | `#9b70ff` |
| 4     | `#794aff` |
| 5     | `#2d0fbf` |
| 6     | `#0b0074` |

### Purple

| Shade | Hex       |
|-------|-----------|
| 1     | `#fdf4ff` |
| 2     | `#f7d9ff` |
| 3     | `#d150ff` |
| 4     | `#b01fe3` |
| 5     | `#660087` |
| 6     | `#3a004f` |

### Magenta

| Shade | Hex       |
|-------|-----------|
| 1     | `#fff3fc` |
| 2     | `#ffd7f6` |
| 3     | `#f911e0` |
| 4     | `#ca00b6` |
| 5     | `#740068` |
| 6     | `#44003c` |

### Pink

| Shade | Hex       |
|-------|-----------|
| 1     | `#fff7fb` |
| 2     | `#ffdcec` |
| 3     | `#ff2fb2` |
| 4     | `#d2008f` |
| 5     | `#790051` |
| 6     | `#4b0030` |
