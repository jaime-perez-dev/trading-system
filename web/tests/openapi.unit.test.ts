import { describe, it, expect } from 'vitest'
import fs from 'fs/promises'
import path from 'path'
import yaml from 'yaml'

const OPENAPI_FILE = path.join(process.cwd(), 'openapi.yaml')

describe('OpenAPI Specification', () => {
  let spec: Record<string, unknown>

  // Load spec before tests
  it('loads valid YAML', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    expect(spec).toBeDefined()
  })

  it('has required OpenAPI fields', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    expect(spec.openapi).toBe('3.1.0')
    expect(spec.info).toBeDefined()
    expect((spec.info as Record<string, unknown>).title).toBe('EdgeSignals API')
    expect((spec.info as Record<string, unknown>).version).toBe('1.0.0')
  })

  it('defines all main endpoints', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    const paths = spec.paths as Record<string, unknown>
    expect(paths).toBeDefined()
    
    // Core endpoints
    expect(paths['/api/health']).toBeDefined()
    expect(paths['/api/signals']).toBeDefined()
    expect(paths['/api/track-record']).toBeDefined()
    expect(paths['/api/feed']).toBeDefined()
    expect(paths['/api/waitlist']).toBeDefined()
  })

  it('defines auth endpoints', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    const paths = spec.paths as Record<string, unknown>
    expect(paths['/api/auth/signup']).toBeDefined()
  })

  it('defines payment endpoints', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    const paths = spec.paths as Record<string, unknown>
    expect(paths['/api/dodo/checkout']).toBeDefined()
    expect(paths['/api/lemonsqueezy/checkout']).toBeDefined()
  })

  it('defines notification endpoints', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    const paths = spec.paths as Record<string, unknown>
    expect(paths['/api/notifications/subscribe']).toBeDefined()
    expect(paths['/api/notifications/unsubscribe']).toBeDefined()
  })

  it('defines Signal schema correctly', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    const schemas = (spec.components as Record<string, unknown>)?.schemas as Record<string, unknown>
    expect(schemas).toBeDefined()
    
    const signal = schemas.Signal as Record<string, unknown>
    expect(signal).toBeDefined()
    expect(signal.type).toBe('object')
    
    const required = signal.required as string[]
    expect(required).toContain('id')
    expect(required).toContain('date')
    expect(required).toContain('headline')
    expect(required).toContain('market')
    expect(required).toContain('signal')
    expect(required).toContain('status')
  })

  it('defines rate limit response', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    const responses = (spec.components as Record<string, unknown>)?.responses as Record<string, unknown>
    expect(responses).toBeDefined()
    expect(responses.RateLimitExceeded).toBeDefined()
    
    const rateLimitResponse = responses.RateLimitExceeded as Record<string, unknown>
    expect(rateLimitResponse.description).toBe('Rate limit exceeded')
    expect(rateLimitResponse.headers).toBeDefined()
  })

  it('defines security schemes', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    const securitySchemes = (spec.components as Record<string, unknown>)?.securitySchemes as Record<string, unknown>
    expect(securitySchemes).toBeDefined()
    expect(securitySchemes.bearerAuth).toBeDefined()
    expect(securitySchemes.cookieAuth).toBeDefined()
  })

  it('has valid server URLs', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    const servers = spec.servers as Array<Record<string, unknown>>
    expect(servers).toBeDefined()
    expect(servers.length).toBeGreaterThanOrEqual(2)
    
    const urls = servers.map(s => s.url)
    expect(urls).toContain('https://edgesignals.ai')
    expect(urls).toContain('http://localhost:3000')
  })

  it('defines all required schemas', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    const schemas = (spec.components as Record<string, unknown>)?.schemas as Record<string, unknown>
    
    const requiredSchemas = [
      'Signal',
      'SignalsResponse',
      'TrackRecordResponse',
      'HealthResponse',
      'User',
      'Error',
      'RateLimitError',
    ]
    
    for (const schema of requiredSchemas) {
      expect(schemas[schema]).toBeDefined()
    }
  })

  it('health endpoint is marked as public', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    const paths = spec.paths as Record<string, unknown>
    const healthPath = paths['/api/health'] as Record<string, unknown>
    const getOp = healthPath.get as Record<string, unknown>
    
    // Should have empty security array (public)
    expect(getOp.security).toEqual([])
  })

  it('feed endpoint is marked as public', async () => {
    const content = await fs.readFile(OPENAPI_FILE, 'utf-8')
    spec = yaml.parse(content)
    
    const paths = spec.paths as Record<string, unknown>
    const feedPath = paths['/api/feed'] as Record<string, unknown>
    const getOp = feedPath.get as Record<string, unknown>
    
    expect(getOp.security).toEqual([])
  })
})
