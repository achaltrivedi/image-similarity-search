const API_BASE_URL = '/api'

export async function searchImage(file, topK = 10) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('top_k', topK)

    const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        body: formData,
    })

    if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
    }

    return await response.json()
}
