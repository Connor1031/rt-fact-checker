// frontend/public/background.js
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch((error) => console.error(error));

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "verify-aegis-text",
    title: "Verify Text with Aegis",
    contexts: ["selection"] 
  });

  // A unified image scanner that shows up on images AND general page elements
  chrome.contextMenus.create({
    id: "verify-aegis-image",
    title: "Verify Image with Aegis",
    contexts: ["image", "page"] 
  });

// Full Page Scanner
  chrome.contextMenus.create({
    id: "verify-aegis-page",
    title: "Scan Full Article with Aegis",
    contexts: ["page"] 
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {

  // 1. OPEN THE PANEL IMMEDIATELY
  chrome.sidePanel.open({ windowId: tab.windowId }).catch((err) => console.error(err));
  if (info.selectionText) {
    chrome.runtime.sendMessage({ 
      action: 'analyze_new_data', 
      text: info.selectionText 
    }).catch(() => {});
  } 
  else if (info.srcUrl) {
    chrome.runtime.sendMessage({ 
      action: 'analyze_new_data', 
      imageUrl: info.srcUrl 
    }).catch(() => {});
  }
  
  // 2. SAVE THE DATA
  // Handle Text Scan
  if (info.menuItemId === "verify-aegis-text") {
    chrome.storage.local.set({ 
      aegis_context_text: info.selectionText,
      aegis_context_image: null 
    });
  } 
  
  // Handle Image Scan
  else if (info.menuItemId === "verify-aegis-image") {
    if (info.srcUrl) {
      chrome.storage.local.set({ 
        aegis_context_image: info.srcUrl,
        aegis_context_text: null 
      });
    } 
    else {
      chrome.tabs.sendMessage(tab.id, { action: "getXRayImage" }, (response) => {
        if (chrome.runtime.lastError) {
          console.error("Content script not injected yet. Reload the page.");
          return;
        }
        
        if (response && response.imageUrl) {
          chrome.storage.local.set({ 
            aegis_context_image: response.imageUrl,
            aegis_context_text: null 
          });
        }
      });
    }
  }

  // Handle Full Page Scan
  else if (info.menuItemId === "verify-aegis-page") {
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      function: scrapeArticleText,
    }, (results) => {
      if (results && results[0] && results[0].result) {
        const pageText = results[0].result;
        chrome.storage.local.set({ 
          aegis_context_text: pageText,
          aegis_context_image: null
        }); 
      } else {
        console.error("Failed to extract text from the page.");
      }
    });
  }
});

// The Scraping Function
// This function runs INSIDE the web page to grab the text
function scrapeArticleText() {
  let content = "";

  const articleTag = document.querySelector('article');
  const mainTag = document.querySelector('main');
  
  if (articleTag) {
    content = articleTag.innerText;
  } else if (mainTag) {
    content = mainTag.innerText;
  } else {
    // Fallback: Just grab all paragraph text
    const paragraphs = Array.from(document.querySelectorAll('p'));
    content = paragraphs.map(p => p.innerText).join('\n\n');
  }

  // Limit the text to roughly the first 8000 characters
  return content.substring(0, 8000).trim();
}