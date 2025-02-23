document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const generateBtn = document.getElementById('generate-btn');
    const downloadBtn = document.getElementById('download-btn');
    const resultDiv = document.getElementById('result');
    const imageElement = document.getElementById('generated-image');

    // Dark mode toggle
    themeToggle.addEventListener('click', () => {
        document.body.dataset.theme =
            document.body.dataset.theme === 'dark' ? 'light' : 'dark';
    });

    // Generate image
    generateBtn.addEventListener('click', async () => {
        const prompt = document.getElementById('prompt').value;

        try {
            generateBtn.disabled = true;
            generateBtn.textContent = 'Generating...';

            const response = await fetch('/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: prompt
                })
            });

            if (!response.ok) {
                // Try to get error details from response
                let errorMessage = `Server error (${response.status})`;
                try {
                    const errorData = await response.json();
                    if (errorData.error) {
                        errorMessage = errorData.error;
                    }
                } catch (e) {
                    // If we can't parse the error response, stick with default message
                    console.error('Could not parse error response:', e);
                }
                throw new Error(errorMessage);
            }

            const contentType = response.headers.get("content-type");
            if (!contentType || !contentType.includes("application/json")) {
                throw new Error("Server returned non-JSON response");
            }

            const data = await response.json();
            if (!data.image_url) {
                throw new Error("No image URL in response");
            }

            imageElement.src = data.image_url;
            resultDiv.classList.remove('hidden');
        } catch (error) {
            console.error('Error details:', error);
            alert(`Failed to generate image: ${error.message}`);
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate Image';
        }
    });

    // Download image
    downloadBtn.addEventListener('click', () => {
        const link = document.createElement('a');
        link.href = imageElement.src;
        link.download = 'generated-image.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
});