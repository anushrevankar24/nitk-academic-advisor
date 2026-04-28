import React, { useState, useEffect, useRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist';

// Use local worker instead of CDN for reliability in React
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

function PdfCanvas({ filename, targetPage, chunkText, onStatus, scale = 1.0 }) {
  const [doc, setDoc] = useState(null);
  const [pageCount, setPageCount] = useState(0);
  const wrapperRef = useRef(null);
  const renderTasksRef = useRef([]);

  useEffect(() => {
    let active = true;
    const loadPdf = async () => {
      onStatus({ type: 'loading', msg: 'Loading PDF...' });
      try {
        const url = `/pdf/${encodeURIComponent(filename)}`;
        const loadingTask = pdfjsLib.getDocument(url);
        const loadedDoc = await loadingTask.promise;
        if (!active) return;
        
        setDoc(loadedDoc);
        setPageCount(loadedDoc.numPages);
        onStatus({ type: 'info', msg: `Page ${targetPage} of ${loadedDoc.numPages}` });
      } catch (err) {
        if (!active) return;
        onStatus({ type: 'error', msg: `Could not load PDF: ${err.message}` });
      }
    };
    
    // Cleanup previous completely on filename change
    setDoc(null);
    if (wrapperRef.current) {
        wrapperRef.current.innerHTML = '';
    }
    
    loadPdf();

    return () => {
      active = false;
      renderTasksRef.current.forEach(t => { try { t.cancel(); } catch(e){} });
      renderTasksRef.current = [];
    };
  }, [filename, targetPage, onStatus]);

  useEffect(() => {
    if (!doc || !wrapperRef.current) return;
    
    const wrapper = wrapperRef.current;
    wrapper.innerHTML = ''; // Start fresh
    
    // Create placeholders
    const containers = [];
    for (let p = 1; p <= pageCount; p++) {
        const container = document.createElement('div');
        container.className = 'pdf-page-container';
        container.id = `pdf-page-${p}`;
        container.dataset.page = p;
        container.dataset.rendered = 'false';
        container.style.minHeight = '840px';
        container.style.width = '600px';
        container.style.background = '#fff';
        wrapper.appendChild(container);
        containers.push(container);
    }
    
    const renderSinglePage = async (pageNum, container) => {
        if (container.dataset.rendered === 'true') return;
        try {
            const page = await doc.getPage(pageNum);
            const panelWidth = wrapper.clientWidth || 480;
            const viewport = page.getViewport({ scale: 1 });
            
            // Calculate base scale to fit panel, multiplied by user zoom scale
            const baseScale = Math.min((panelWidth - 24) / viewport.width, 1.6);
            const finalScale = baseScale * scale;
            const scaledViewport = page.getViewport({ scale: finalScale });

            container.innerHTML = '';
            container.style.minHeight = '';
            container.style.width = `${scaledViewport.width}px`;
            container.style.position = 'relative';

            // High DPI Canvas Rendering
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            const outputScale = window.devicePixelRatio || 1;

            canvas.width = Math.floor(scaledViewport.width * outputScale);
            canvas.height = Math.floor(scaledViewport.height * outputScale);
            canvas.style.width = `${Math.floor(scaledViewport.width)}px`;
            canvas.style.height = `${Math.floor(scaledViewport.height)}px`;
            
            const transform = outputScale !== 1 
                ? [outputScale, 0, 0, outputScale, 0, 0] 
                : null;

            container.appendChild(canvas);

            const renderTask = page.render({
                canvasContext: context,
                transform: transform,
                viewport: scaledViewport,
            });
            renderTasksRef.current.push(renderTask);
            await renderTask.promise;

            const textContent = await page.getTextContent();
            const textLayer = document.createElement('div');
            textLayer.className = 'pdf-text-layer';
            textLayer.style.width = `${Math.floor(scaledViewport.width)}px`;
            textLayer.style.height = `${Math.floor(scaledViewport.height)}px`;
            textLayer.style.position = 'absolute';
            textLayer.style.top = '0';
            textLayer.style.left = '0';
            container.appendChild(textLayer);

            renderTextLayer(textContent, textLayer, scaledViewport);
            container.dataset.rendered = 'true';
            
            // Only attempt highlight after target page renders
            if (pageNum === targetPage) {
               applyHighlight(chunkText, onStatus);
            }
        } catch (err) {
            if (err.name !== 'RenderingCancelledException') {
                console.warn(`Page ${pageNum} render error:`, err);
            }
        }
    };

    // Render target page first
    const targetContainer = containers[targetPage - 1];
    if (targetContainer) {
        renderSinglePage(targetPage, targetContainer).then(() => {
            targetContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    // Intersection observer for lazy rendering
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const pageNum = parseInt(el.dataset.page, 10);
                if (el.dataset.rendered === 'false') {
                    el.dataset.rendered = 'pending';
                    renderSinglePage(pageNum, el).then(() => {
                        el.dataset.rendered = 'true';
                    });
                }
            }
        });
    }, {
        root: wrapper,
        rootMargin: '200px',
        threshold: 0.01
    });

    containers.forEach((c, i) => {
        if (i + 1 !== targetPage) {
            observer.observe(c);
        }
    });

    return () => {
        observer.disconnect();
    };
  }, [doc, pageCount, targetPage, chunkText, onStatus, scale]);

  // Apply highlight directly if targetPage or chunkText changes on an already rendered page
  useEffect(() => {
      const container = document.getElementById(`pdf-page-${targetPage}`);
      if (container && container.dataset.rendered === 'true') {
          container.scrollIntoView({ behavior: 'smooth', block: 'start' });
          applyHighlight(chunkText, onStatus);
      }
  }, [targetPage, chunkText, onStatus]);

  return <div id="pdfViewerArea" className="pdf-viewer-area" ref={wrapperRef}></div>;
}

function renderTextLayer(textContent, container, viewport) {
    const { items } = textContent;
    items.forEach(item => {
        if (!item.str || item.str.trim() === '') return;

        const tx = pdfjsLib.Util.transform(viewport.transform, item.transform);
        const angle = Math.atan2(tx[1], tx[0]);
        const fontSize = Math.sqrt(tx[2] * tx[2] + tx[3] * tx[3]);

        const span = document.createElement('span');
        span.textContent = item.str;
        span.style.fontSize = `${fontSize}px`;
        span.style.fontFamily = item.fontName || 'sans-serif';
        span.style.left = `${tx[4]}px`;
        span.style.top = `${tx[5] - fontSize}px`;

        if (Math.abs(angle) > 0.01) {
            span.style.transform = `rotate(${-angle}rad)`;
        }

        if (item.width) {
            const scaleX = item.width * viewport.scale / (item.str.length * fontSize * 0.55 || 1);
            if (scaleX < 0.98 || scaleX > 1.02) {
                span.style.transform = (span.style.transform || '') + ` scaleX(${scaleX.toFixed(3)})`;
            }
        }

        container.appendChild(span);
    });
}

function applyHighlight(chunkText, onStatus) {
    if (!chunkText) return;

    // Use extreme normalization: remove all non-alphanumeric chars to match reliably across PDF rendering artifacts
    const extremeNormalize = (str) => str.replace(/[^\w]/g, '').toLowerCase();
    
    // Pick the first large chunk to find the starting point.
    const fullNormalizedChunk = extremeNormalize(chunkText);
    const searchStr = fullNormalizedChunk.slice(0, 80); // try to find first 80 chars
    if (searchStr.length < 10) return;

    let matchCount = 0;

    // Clear old highlights first
    document.querySelectorAll('.pdf-highlight-mark').forEach(el => {
        el.classList.remove('pdf-highlight-mark');
    });

    document.querySelectorAll('.pdf-text-layer').forEach(layer => {
        const spans = Array.from(layer.querySelectorAll('span'));
        if (spans.length === 0) return;

        let combined = '';
        const boundaries = [];
        spans.forEach(span => {
            const t = extremeNormalize(span.textContent);
            boundaries.push({ start: combined.length, end: combined.length + t.length, span });
            combined += t;
        });

        // Find start index
        const idx = combined.indexOf(searchStr);
        if (idx === -1) { console.warn("PdfCanvas: Highlighting failed. Text chunk not found on this page.", searchStr); return; }

        // Find end index based on total length of normal chunk
        const endIdx = idx + fullNormalizedChunk.length;

        boundaries.forEach(({ start, end, span }) => {
            if (end > idx && start < endIdx) {
                span.classList.add('pdf-highlight-mark');
                matchCount++;
            }
        });
    });

    if (matchCount > 0) {
        onStatus({ type: 'success', msg: `Highlighted source evidence` });
        const first = document.querySelector('.pdf-highlight-mark');
        if (first) {
            setTimeout(() => {
                first.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 100);
        }
    } else {
        onStatus({ type: 'warning', msg: 'Exact text match not found — navigated to source page' });
    }
}

export default PdfCanvas;
