// frontend/public/background.js

chrome.runtime.onInstalled.addListener(() => {
  // Create menu for highlighted text
  chrome.contextMenus.create({
    id: "verify-aegis-text",
    title: "Verify Text with Aegis",
    contexts: ["selection"] 
  });

  // Create menu for images
  chrome.contextMenus.create({
    id: "verify-aegis-image",
    title: "Verify Image with Aegis",
    contexts: ["image"] 
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "verify-aegis-text") {
    // Save text
    chrome.storage.local.set({ 
      aegis_context_text: info.selectionText,
      aegis_context_image: null // Clear any old images
    }, () => {
      chrome.action.openPopup();
    });
  } 
  else if (info.menuItemId === "verify-aegis-image") {
    // Save image URL
    chrome.storage.local.set({ 
      aegis_context_image: info.srcUrl,
      aegis_context_text: null // Clear any old text
    }, () => {
      chrome.action.openPopup();
    });
  }
});