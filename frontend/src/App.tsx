import { BrowserRouter, Route, Routes } from "react-router-dom";
import { SiteLayout } from "./components/SiteLayout";
import { MarketplaceProvider } from "./features/marketplace/MarketplaceContext";
import {
  CartPage,
  CheckoutPage,
  HomePage,
  LoginPage,
  MyOrdersPage,
  NotFoundPage,
  OrderDetailPage,
  OrderSuccessPage,
  PaymentPage,
  ProductDetailPage,
  ProductsPage,
  ProfilePage,
  RegisterPage,
  SellerProductsPage,
} from "./pages/Pages";

export default function App() {
  return (
    <MarketplaceProvider>
      <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
        <Routes>
          <Route element={<SiteLayout />}>
            <Route index element={<HomePage />} />
            <Route path="products" element={<ProductsPage />} />
            <Route path="products/:productId" element={<ProductDetailPage />} />
            <Route path="cart" element={<CartPage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="register" element={<RegisterPage />} />
            <Route path="checkout" element={<CheckoutPage />} />
            <Route path="order-success" element={<OrderSuccessPage />} />
            <Route path="account/orders" element={<MyOrdersPage />} />
            <Route path="account/orders/:orderId" element={<OrderDetailPage />} />
            <Route path="account/orders/:orderId/pay" element={<PaymentPage />} />
            <Route path="account/profile" element={<ProfilePage />} />
            <Route path="seller" element={<SellerProductsPage />} />
            <Route path="seller/products" element={<SellerProductsPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </MarketplaceProvider>
  );
}
