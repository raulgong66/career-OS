import type { Profile } from '../types';

export class ProfileService {
  private static instance: ProfileService;

  private constructor() {}

  static getInstance(): ProfileService {
    if (!ProfileService.instance) {
      ProfileService.instance = new ProfileService();
    }
    return ProfileService.instance;
  }

  async uploadProfile(_file: File): Promise<Profile> {
    // Mock implementation - in production this would call the backend API
    return new Promise((resolve) => {
      setTimeout(() => {
        const mockProfile: Profile = {
          id: 'mock-profile-1',
          person: {
            firstName: 'John',
            lastName: 'Doe',
          },
          artifacts: [
            {
              id: 'cv-english-source',
              type: 'cv',
              name: 'Software Engineer CV',
              sourceRefs: [],
            },
          ],
        };
        resolve(mockProfile);
      }, 500);
    });
  }

  async getProfile(profileId: string): Promise<Profile> {
    // Mock implementation
    return new Promise((resolve) => {
      setTimeout(() => {
        const mockProfile: Profile = {
          id: profileId,
          person: {
            firstName: 'John',
            lastName: 'Doe',
          },
          artifacts: [
            {
              id: 'cv-english-source',
              type: 'cv',
              name: 'Software Engineer CV',
              sourceRefs: [],
            },
          ],
        };
        resolve(mockProfile);
      }, 300);
    });
  }
}
