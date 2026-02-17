const API_BASE_URL = '/api'

export async function searchImage(file, pageSize = 50, similarityThreshold = 0.0) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('page', 1)
    formData.append('page_size', pageSize)
    formData.append('similarity_threshold', similarityThreshold)

    const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        body: formData,
    })

    if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`)
    }

    return await response.json()
}

export async function searchNextPage(queryId, page, pageSize = 50, similarityThreshold = 0.0) {
    const formData = new FormData()
    formData.append('query_id', queryId)
    formData.append('page', page)
    formData.append('page_size', pageSize)
    formData.append('similarity_threshold', similarityThreshold)

    const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        body: formData,
    })

    if (!response.ok) {
        throw new Error(`Failed to load page ${page}: ${response.statusText}`)
    }

    return await response.json()
}
