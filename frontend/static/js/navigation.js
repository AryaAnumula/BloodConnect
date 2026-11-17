for (const link of document.querySelectorAll('.sidebar-nav .nav-link')) {
  if (new URL(link.href, window.location.origin).pathname === window.location.pathname) link.setAttribute('aria-current', 'page');
}
