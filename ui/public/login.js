// The sign-in name is optional, but Chainlit's /login needs one: send "guest" when it's left blank.
document.addEventListener("click", (event) => {
  const button = event.target.closest && event.target.closest('button[type="submit"]');
  const name = document.getElementById("email");
  if (!button || !name || name.value.trim()) return;
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(name, "guest");
  name.dispatchEvent(new Event("input", { bubbles: true }));
}, true);
