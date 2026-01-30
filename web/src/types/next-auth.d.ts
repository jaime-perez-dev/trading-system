import { DefaultSession, DefaultUser } from "next-auth"
import { JWT, DefaultJWT } from "next-auth/jwt"

declare module "next-auth" {
  interface Session {
    user: {
      id: string
      tier: string
    } & DefaultSession["user"]
  }

  interface User extends DefaultUser {
    tier: string
  }
}

declare module "next-auth/jwt" {
  interface JWT extends DefaultJWT {
    tier?: string
  }
}
