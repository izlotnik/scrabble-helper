function scrambleInput(inputId) {
  const input = document.getElementById(inputId);
  const chars = input.value.split('');
  for (let i = chars.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [chars[i], chars[j]] = [chars[j], chars[i]];
  }
  input.value = chars.join('');
  input.focus();
}

// Guarantee Enter submits the enclosing form from any text or number input,
// regardless of browser quirks with multi-input forms or nested layouts.
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('form input[type="text"], form input[type="number"]').forEach(function (input) {
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        const form = this.closest('form');
        if (form) {
          e.preventDefault();
          form.requestSubmit();
        }
      }
    });
  });
});
