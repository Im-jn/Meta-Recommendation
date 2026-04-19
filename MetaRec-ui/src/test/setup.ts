import '@testing-library/jest-dom'

if (!('scrollTo' in HTMLElement.prototype)) {
  Object.defineProperty(HTMLElement.prototype, 'scrollTo', {
    value: () => {},
    writable: true,
  })
}
