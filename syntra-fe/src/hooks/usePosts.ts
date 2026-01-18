import { useQuery } from '@tanstack/react-query';
import { getPosts, type Post } from '../services/postService';

export const usePosts = () => {
    return useQuery<Post[], Error>({
        queryKey: ['posts'],
        queryFn: getPosts,
    });
};
