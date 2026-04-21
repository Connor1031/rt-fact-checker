// frontend/public/content.js

// 1. Track exactly where the user right-clicks
let lastRightClickEvent = null;

document.addEventListener('contextmenu', (event) => {
    lastRightClickEvent = event;
}, true);

// 2. Listen for Aegis asking for the hidden image
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getXRayImage") {
    if (!lastRightClickEvent) {
        sendResponse({ imageUrl: null });
        return true;
    }

    const x = lastRightClickEvent.clientX;
    const y = lastRightClickEvent.clientY;

    // Grab the shield element we just clicked
    const shield = document.elementFromPoint(x, y);
    let foundImageUrl = null;

    if (shield) {
      // Temporarily hide the shield
        const originalPointerEvents = shield.style.pointerEvents;
        shield.style.pointerEvents = 'none'; 

      // Look at the element sitting right underneath it
        const elementUnderneath = document.elementFromPoint(x, y);

      // Check if it's an image
        if (elementUnderneath && elementUnderneath.tagName === 'IMG') {
        foundImageUrl = elementUnderneath.src;
        } else {
        // Fallback: Just look for any image inside the parent container
        const closestImg = shield.parentElement.querySelector('img');
        if (closestImg) {
            foundImageUrl = closestImg.src;
        }
    }

      // Restore the shield so we don't break the website
        shield.style.pointerEvents = originalPointerEvents;
    }

    sendResponse({ imageUrl: foundImageUrl });
}
return true;
});